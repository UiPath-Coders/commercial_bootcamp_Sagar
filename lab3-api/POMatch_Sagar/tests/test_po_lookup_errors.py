"""po_lookup error paths with the HTTP layer mocked (httpx.MockTransport). No network."""

from __future__ import annotations

import httpx
import pytest

import main
from main import POLookupInput, po_lookup

SAMPLE = POLookupInput(vendor_name="Vertex Analytics Corp.", po_number="PO-2026-0405", invoice_total=22700, currency="USD")


def assert_failed(out, error_type: str):
    assert out.error_type == error_type
    assert out.error_message, "error_message must explain the failure"
    # fail safe: never claim a match, always route to a human
    assert out.po_matched is False
    assert out.approval_required is True
    assert out.match_reason == ""


def test_sends_the_documented_request_body(mock_erp):
    seen = {}

    def handler(request: httpx.Request):
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["json"] = httpx.Response(200, content=request.content).json()
        return httpx.Response(200, json={"po": {"found": True, "vendorActive": True, "openAmount": 22700.0, "currency": "USD"}})

    mock_erp(handler)
    out = po_lookup(SAMPLE)
    assert seen == {
        "method": "POST",
        "path": "/api/po-lookup",
        "json": {"vendorName": "Vertex Analytics Corp.", "poNumber": "PO-2026-0405", "invoiceTotal": 22700.0, "currency": "USD"},
    }
    assert out.error_type == "" and out.po_matched is True and out.approval_required is True


def test_uses_erp_api_url_env_var(mock_erp, monkeypatch):
    monkeypatch.setenv("ERP_API_URL", "https://erp.example.test/base/")
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"po": {"found": False, "vendorActive": False, "openAmount": 0, "currency": "USD"}})

    mock_erp(handler)
    po_lookup(SAMPLE)
    assert seen["url"] == "https://erp.example.test/base/api/po-lookup"


def test_sends_bearer_token_from_environment_without_exposing_it_in_the_input(mock_erp, monkeypatch):
    monkeypatch.setenv("ERP_API_TOKEN", "signed-participant-token")
    seen = {}

    def handler(request: httpx.Request):
        seen["authorization"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"po": {"found": True, "vendorActive": True, "openAmount": 22700.0, "currency": "USD"}})

    mock_erp(handler)
    po_lookup(SAMPLE)
    assert seen["authorization"] == "Bearer signed-participant-token"


@pytest.mark.parametrize("status", [400, 401, 404, 500, 503])
def test_non_200_status(mock_erp, status):
    mock_erp(lambda request: httpx.Response(status, json={"error": "boom"}))
    out = po_lookup(SAMPLE)
    assert_failed(out, "ERP_HTTP_ERROR")
    assert str(status) in out.error_message


def test_non_json_body(mock_erp):
    mock_erp(lambda request: httpx.Response(200, text="<html>maintenance</html>"))
    assert_failed(po_lookup(SAMPLE), "ERP_MALFORMED_RESPONSE")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"result": "ok"},
        {"po": None},
        {"po": []},
        {"po": {"found": "yes", "vendorActive": True, "openAmount": 22700}},
        {"po": {"found": True, "vendorActive": "active", "openAmount": 22700}},
        {"po": {"found": True, "vendorActive": True, "openAmount": "22700"}},
        {"po": {"found": True, "vendorActive": True}},
    ],
    ids=["empty", "no-po", "po-null", "po-list", "found-str", "active-str", "amount-str", "amount-missing"],
)
def test_malformed_po_object_is_never_guessed(mock_erp, body):
    mock_erp(lambda request: httpx.Response(200, json=body))
    assert_failed(po_lookup(SAMPLE), "ERP_MALFORMED_RESPONSE")


def test_connection_refused(mock_erp):
    def handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused", request=request)

    mock_erp(handler)
    out = po_lookup(SAMPLE)
    assert_failed(out, "ERP_UNREACHABLE")
    assert "ConnectError" in out.error_message


def test_timeout(mock_erp):
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("timed out", request=request)

    mock_erp(handler)
    assert_failed(po_lookup(SAMPLE), "ERP_UNREACHABLE")


def test_blank_po_number_does_not_call_the_erp(mock_erp):
    calls = []
    mock_erp(lambda request: calls.append(request) or httpx.Response(200, json={}))
    out = po_lookup(POLookupInput(vendor_name="x", po_number="  ", invoice_total=10))
    assert_failed(out, "INVALID_INPUT")
    assert calls == []


def test_success_clears_error_fields(mock_erp):
    mock_erp(lambda request: httpx.Response(200, json={"po": {"found": True, "vendorActive": True, "openAmount": 4200.0, "currency": "USD"}}))
    out = po_lookup(POLookupInput(vendor_name="Northwind Office Supplies", po_number="PO-2026-0431", invoice_total=4155.40))
    assert out.model_dump() == {
        "po_matched": True,
        "approval_required": False,
        "open_amount": 4200.0,
        "match_reason": "MATCHED",
        "error_type": "",
        "error_message": "",
    }


def test_po_lookup_never_raises(mock_erp):
    """Even an unexpected transport failure is returned, not raised (Coded Function contract)."""

    def handler(request: httpx.Request):
        raise httpx.RemoteProtocolError("server disconnected", request=request)

    mock_erp(handler)
    out = po_lookup(SAMPLE)  # must not raise
    assert out.error_type == "ERP_UNREACHABLE"


def test_default_erp_url_is_localhost_8080(monkeypatch):
    monkeypatch.delenv("ERP_API_URL", raising=False)
    assert main.erp_api_url() == "http://localhost:8080"


def test_default_po_lookup_url_is_the_local_mock_erp(monkeypatch):
    monkeypatch.delenv("ERP_API_URL", raising=False)
    monkeypatch.delenv("ERP_PO_LOOKUP_URL", raising=False)
    assert main.erp_po_lookup_url() == "http://localhost:8080/api/po-lookup" == main.DEFAULT_ERP_PO_LOOKUP_URL


SIGNED_URL = "https://erp.example.test/api/po-lookup?access_token=SECRET-SIGNED-TOKEN&cohort=c1"


def test_erp_po_lookup_url_is_used_exactly_and_wins_over_erp_api_url(mock_erp, monkeypatch):
    """The complete signed URL is posted to as is: no path appended, query (access_token) kept."""
    monkeypatch.setenv("ERP_API_URL", "https://legacy.example.test/base")
    monkeypatch.setenv("ERP_PO_LOOKUP_URL", f"  {SIGNED_URL}  ")
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"po": {"found": True, "vendorActive": True, "openAmount": 22700.0, "currency": "USD"}})

    mock_erp(handler)
    out = po_lookup(SAMPLE)
    assert seen["url"] == SIGNED_URL
    assert out.error_type == "" and out.po_matched is True


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(401, text=f"bad token for {request.url}"),
        lambda request: httpx.Response(200, text="<html>not json</html>"),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError(f"cannot reach {request.url}", request=request)),
    ],
    ids=["http-error-echoing-url", "non-json", "connect-error"],
)
def test_access_token_never_appears_in_error_messages(mock_erp, monkeypatch, caplog, handler):
    monkeypatch.setenv("ERP_PO_LOOKUP_URL", SIGNED_URL)
    mock_erp(handler)
    with caplog.at_level("DEBUG", logger="POMatch_Sagar"):
        out = po_lookup(SAMPLE)
    assert out.error_type in {"ERP_HTTP_ERROR", "ERP_MALFORMED_RESPONSE", "ERP_UNREACHABLE"}
    assert "SECRET-SIGNED-TOKEN" not in out.error_message
    assert "access_token=***" in out.error_message
    assert "SECRET-SIGNED-TOKEN" not in caplog.text


def test_redact_hides_every_access_token_value():
    text = "GET https://h/x?access_token=abc.def-123&b=1 and ACCESS_TOKEN=zzz"
    assert main.redact(text) == "GET https://h/x?access_token=***&b=1 and ACCESS_TOKEN=***"
