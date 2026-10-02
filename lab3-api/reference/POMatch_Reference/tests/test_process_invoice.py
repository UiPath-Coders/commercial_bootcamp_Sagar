"""process_invoice, get_invoice_status, queue delegation and transaction completion.

Same in-memory SDK fake and mocked ERP as test_process_invoice_queue.py (fixtures reused from there).
"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

import main
from main import (
    InvoiceStatusInput,
    ProcessInvoiceInput,
    ProcessQueueInput,
    get_invoice_status,
    process_invoice,
    process_invoice_queue,
)
from test_process_invoice_queue import (  # noqa: F401 - fixtures are used by name
    ENTITY_ID,
    FakeEntities,
    FakeQueues,
    erp,
    fake_sdk,
    record,
    tx,
)

NORTHWIND = record("Northwind Office Supplies", "PO-2026-0431", 4155.40)  # MATCHED, no approval


class ReadOnlyEntities(FakeEntities):
    """Fails the test on any write method, so 'read-only' is enforced, not just observed."""

    def _write(self, *args, **kwargs):
        raise AssertionError("get_invoice_status must not write")

    update_record = insert_record = delete_record = update_records = insert_records = delete_records = _write


# --------------------------------------------------------------------------------------
# process_invoice
# --------------------------------------------------------------------------------------


def test_process_invoice_reads_matches_and_writes_the_same_record(fake_sdk, erp):
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({"rec-001": NORTHWIND, "rec-002": record("Contoso", "PO-2026-0447", 12740.0)}))

    out = process_invoice(ProcessInvoiceInput(record_id="rec-001"))

    assert out.model_dump() == {
        "record_id": "rec-001",
        "po_matched": True,
        "approval_required": False,
        "open_amount": 4200.0,
        "match_reason": "MATCHED",
        "error_type": "",
        "error_message": "",
    }
    assert entities.updates == [(ENTITY_ID, "rec-001", {"POMatched": True, "ApprovalNeeded": False})]
    assert entities.records["rec-002"]["POMatched"] is None  # no other record touched
    assert erp == [{"vendorName": "Northwind Office Supplies", "poNumber": "PO-2026-0431", "invoiceTotal": 4155.40, "currency": "USD"}]
    assert queues.started == [] and queues.completed == []  # no queue work


def test_process_invoice_rerun_is_idempotent(fake_sdk):
    _, entities = fake_sdk(FakeQueues([]), FakeEntities({"rec-001": NORTHWIND}))
    first = process_invoice(ProcessInvoiceInput(record_id="rec-001"))
    snapshot = dict(entities.records["rec-001"])
    second = process_invoice(ProcessInvoiceInput(record_id="rec-001"))

    assert first == second
    assert entities.records["rec-001"] == snapshot
    assert len(entities.updates) == 1  # the re-run found the values already in place and skipped the write


def test_process_invoice_uses_the_given_entity_name(fake_sdk):
    _, entities = fake_sdk(FakeQueues([]), FakeEntities({"rec-001": NORTHWIND}, entity_name="AP_Invoice_Axel"))
    out = process_invoice(ProcessInvoiceInput(record_id="rec-001", entity_name="AP_Invoice_Axel"))
    assert out.error_type == ""
    assert entities.lookups == [("by_name", "AP_Invoice_Axel")]


@pytest.mark.parametrize(
    ("records", "record_id", "error_type", "fragment"),
    [
        ({}, "", "INVALID_INPUT", "record_id is required"),
        ({}, "rec-missing", "RECORD_NOT_FOUND", "could not be read"),
        ({"rec-a": record("V", "PO-2026-0431", None)}, "rec-a", "INVALID_RECORD", "TotalAmount is empty"),
        ({"rec-x": record("V", "PO-BROKEN", 100.0)}, "rec-x", "ERP_HTTP_ERROR", "PO lookup failed"),
    ],
    ids=["blank-id", "missing-record", "empty-total", "erp-down"],
)
def test_process_invoice_returns_errors_and_writes_nothing(fake_sdk, records, record_id, error_type, fragment):
    _, entities = fake_sdk(FakeQueues([]), FakeEntities(records))
    out = process_invoice(ProcessInvoiceInput(record_id=record_id))  # must not raise
    assert out.error_type == error_type
    assert fragment in out.error_message
    assert out.po_matched is False and out.approval_required is True  # fail safe
    assert entities.updates == []


def test_process_invoice_reports_update_failure(fake_sdk):
    entities = FakeEntities({"rec-001": NORTHWIND})
    entities.fail_update_for.add("rec-001")
    fake_sdk(FakeQueues([]), entities)
    out = process_invoice(ProcessInvoiceInput(record_id="rec-001"))
    assert out.error_type == "RECORD_UPDATE_FAILED" and "could not be updated" in out.error_message


def test_process_invoice_reports_unknown_entity(fake_sdk):
    fake_sdk(FakeQueues([]), FakeEntities({}))
    out = process_invoice(ProcessInvoiceInput(record_id="rec-001", entity_name="AP_Invoice_Nobody"))
    assert out.error_type == "ENTITY_RESOLUTION_FAILED" and "AP_Invoice_Nobody" in out.error_message


def test_process_invoice_never_logs_confidential_fields(fake_sdk, caplog):
    data = dict(NORTHWIND, VendorTaxId="98-7654321", BankAccount="DE89370400440532013000")
    fake_sdk(FakeQueues([]), FakeEntities({"rec-001": data}))
    with caplog.at_level("DEBUG", logger="POMatch_Reference"):
        process_invoice(ProcessInvoiceInput(record_id="rec-001"))
    assert "rec-001" in caplog.text
    for secret in ("98-7654321", "DE89370400440532013000", "Northwind", "4155.4"):
        assert secret not in caplog.text


# --------------------------------------------------------------------------------------
# Data Fabric casing: reads tolerate PoNumber / PoMatched, writes use PONumber / POMatched
# --------------------------------------------------------------------------------------


def test_reads_tolerate_camel_cased_acronyms_and_writes_use_schema_names(fake_sdk, erp):
    api_shaped = {
        "VendorName": "Northwind Office Supplies",
        "PoNumber": "PO-2026-0431",  # records API spelling of schema field PONumber
        "TotalAmount": 4155.40,
        "Currency": "USD",
        "PoMatched": None,
        "ApprovalNeeded": None,
        "PostedToErp": False,
    }
    _, entities = fake_sdk(FakeQueues([]), FakeEntities({"rec-001": api_shaped}))

    out = process_invoice(ProcessInvoiceInput(record_id="rec-001"))

    assert out.error_type == "" and out.po_matched is True
    assert erp[0]["poNumber"] == "PO-2026-0431"
    assert entities.updates == [(ENTITY_ID, "rec-001", {"POMatched": True, "ApprovalNeeded": False})]

    status = get_invoice_status(InvoiceStatusInput(record_id="rec-001"))
    assert status.posted_to_erp is False and status.found is True


def test_get_field_prefers_exact_then_case_insensitive():
    assert main._get_field({"PONumber": "a", "PoNumber": "b"}, "PONumber") == "a"
    assert main._get_field({"PoNumber": "b"}, "PONumber") == "b"
    assert main._get_field({"postedtoerp": True}, "PostedToERP") is True
    assert main._get_field({}, "ReviewedBy", "") == ""


# --------------------------------------------------------------------------------------
# get_invoice_status (read-only)
# --------------------------------------------------------------------------------------


def test_get_invoice_status_returns_lifecycle_fields_without_writing(fake_sdk):
    data = dict(NORTHWIND, POMatched=True, ApprovalNeeded=True, PostedToERP=False,
                InvoiceLifecycleState="APPROVED", ReviewedBy="reviewer@example.test", ReviewedAt="2026-09-24T10:00:00Z")
    queues, entities = fake_sdk(FakeQueues([]), ReadOnlyEntities({"rec-009": data}))
    before = json.dumps(entities.records, sort_keys=True)

    out = get_invoice_status(InvoiceStatusInput(record_id="rec-009"))

    assert out.model_dump() == {
        "record_id": "rec-009",
        "invoice_lifecycle_state": "APPROVED",
        "approval_needed": True,
        "posted_to_erp": False,
        "reviewed_by": "reviewer@example.test",
        "reviewed_at": "2026-09-24T10:00:00Z",
        "found": True,
        "error_type": "",
        "error_message": "",
    }
    assert entities.updates == []
    assert json.dumps(entities.records, sort_keys=True) == before
    assert queues.started == [] and queues.completed == []


def test_get_invoice_status_on_a_day1_entity_returns_empty_strings(fake_sdk):
    """Day 1 entities have no InvoiceLifecycleState / ReviewedBy / ReviewedAt; that is not an error."""
    day1 = dict(NORTHWIND, POMatched=True, ApprovalNeeded=False, PostedToERP=True)
    _, entities = fake_sdk(FakeQueues([]), ReadOnlyEntities({"rec-001": day1}))  # schema lacks the Lab 6 fields

    out = get_invoice_status(InvoiceStatusInput(record_id="rec-001"))

    assert out.found is True and out.error_type == ""
    assert (out.invoice_lifecycle_state, out.reviewed_by, out.reviewed_at) == ("", "", "")
    assert out.approval_needed is False and out.posted_to_erp is True


def test_get_invoice_status_missing_record_is_not_found(fake_sdk):
    fake_sdk(FakeQueues([]), ReadOnlyEntities({}))
    out = get_invoice_status(InvoiceStatusInput(record_id="rec-nope"))
    assert out.found is False and out.error_type == "RECORD_NOT_FOUND" and out.record_id == "rec-nope"


def test_get_invoice_status_blank_id(fake_sdk):
    _, entities = fake_sdk(FakeQueues([]), ReadOnlyEntities({}))
    out = get_invoice_status(InvoiceStatusInput(record_id="  "))
    assert out.error_type == "INVALID_INPUT" and out.found is False
    assert entities.lookups == []


# --------------------------------------------------------------------------------------
# process_invoice_queue delegates to process_invoice
# --------------------------------------------------------------------------------------


def test_queue_delegates_every_transaction_to_process_invoice(fake_sdk, monkeypatch):
    calls = []
    real = main._process_invoice

    def spy(input, **kwargs):
        calls.append((input.record_id, input.entity_name, kwargs["entity_id"]))
        return real(input, **kwargs)

    monkeypatch.setattr(main, "_process_invoice", spy)

    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-001"), tx("k2", "rec-missing"), tx("k3", "rec-005")]),
        FakeEntities({"rec-001": NORTHWIND, "rec-005": record("Blue Harbor Catering", "PO-2026-0461", 2954.00)}),
    )
    out = process_invoice_queue(ProcessQueueInput())

    assert calls == [
        ("rec-001", "AP_Invoice_Reference", ENTITY_ID),
        ("rec-missing", "AP_Invoice_Reference", ENTITY_ID),
        ("rec-005", "AP_Invoice_Reference", ENTITY_ID),
    ]
    assert (out.processed, out.matched, out.approval_required, out.failed) == (3, 1, 1, 1)
    assert [(c[0], c[1]["IsSuccessful"]) for c in queues.completed] == [(1001, True), (1002, False), (1003, True)]
    assert queues.completed[1][1]["ProcessingException"]["Type"] == "BusinessException"
    assert "RECORD_NOT_FOUND" in out.errors[0]


def test_queue_outcome_follows_process_invoice_result(fake_sdk, monkeypatch):
    """Whatever process_invoice reports decides the transaction status: no rules live in the wrapper."""

    def fake_process_invoice(input, **kwargs):
        if input.record_id == "rec-bad":
            return main.ProcessInvoiceOutput(record_id=input.record_id, error_type="SOMETHING", error_message="nope")
        return main.ProcessInvoiceOutput(record_id=input.record_id, po_matched=True, approval_required=True, match_reason="MATCHED")

    monkeypatch.setattr(main, "_process_invoice", fake_process_invoice)
    queues, entities = fake_sdk(FakeQueues([tx("k1", "rec-ok"), tx("k2", "rec-bad")]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())

    assert (out.processed, out.matched, out.approval_required, out.failed) == (2, 1, 1, 1)
    assert out.errors == ["record rec-bad: SOMETHING: nope"]
    assert queues.completed[0][1] == {"IsSuccessful": True, "Output": {"POMatched": True, "ApprovalNeeded": True, "MatchReason": "MATCHED"}}
    assert queues.completed[1][1]["ProcessingException"] == {"Type": "BusinessException", "Reason": "record rec-bad: SOMETHING: nope"}
    assert entities.updates == []  # the wrapper itself never writes records


def test_transaction_without_numeric_id_is_reported_not_processed(fake_sdk, monkeypatch):
    monkeypatch.setattr(main, "_process_invoice", lambda *a, **k: pytest.fail("must not process an item it cannot complete"))
    item = tx("k1", "rec-001")
    del item["Id"]
    queues, _ = fake_sdk(FakeQueues([item]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())
    assert out.failed == 1 and "no numeric Id" in out.errors[0]
    assert queues.completed == []


# --------------------------------------------------------------------------------------
# _complete: numeric Id, empty 200 body = success, real HTTP errors propagate
# --------------------------------------------------------------------------------------


def test_complete_uses_the_numeric_id(fake_sdk):
    queues, _ = fake_sdk(FakeQueues([]), FakeEntities({}))
    main._complete(1234, {"IsSuccessful": True}, ProcessQueueInput())
    assert queues.completed == [(1234, {"IsSuccessful": True}, "InvoiceQueue_Reference", "Agentic Bootcamp/APAutomation_Reference")]


def test_complete_by_guid_key_would_404(fake_sdk):
    """Documents the original bug: SetTransactionResult by Key is a 404 and must surface."""
    fake_sdk(FakeQueues([]), FakeEntities({}))
    with pytest.raises(httpx.HTTPStatusError):
        main._complete("5c1a2b3d-0000-4000-8000-000000000001", {"IsSuccessful": True}, ProcessQueueInput())


def test_complete_tolerates_empty_body(fake_sdk):
    queues, _ = fake_sdk(FakeQueues([], empty_body=True), FakeEntities({}))
    main._complete(1001, {"IsSuccessful": True}, ProcessQueueInput())  # must not raise
    assert queues.completed[0][0] == 1001

    class PlainValueErrorQueues(FakeQueues):
        def complete_transaction_item(self, *a, **k):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

    fake_sdk(PlainValueErrorQueues([]), FakeEntities({}))
    main._complete(1001, {"IsSuccessful": True}, ProcessQueueInput())  # must not raise


def test_complete_propagates_real_error(fake_sdk):
    class ServerErrorQueues(FakeQueues):
        def complete_transaction_item(self, transaction_key, *a, **k):
            request = httpx.Request("POST", f"https://cloud.test/orchestrator_/odata/Queues({transaction_key})/UiPathODataSvc.SetTransactionResult")
            raise httpx.HTTPStatusError("500 Internal Server Error", request=request, response=httpx.Response(500, request=request))

    fake_sdk(ServerErrorQueues([]), FakeEntities({}))
    with pytest.raises(httpx.HTTPStatusError):
        main._complete(1001, {"IsSuccessful": True}, ProcessQueueInput())

    class InvalidResultQueues(FakeQueues):
        def complete_transaction_item(self, *a, **k):
            raise ValidationError.from_exception_data("TransactionItemResult", [])

    fake_sdk(InvalidResultQueues([]), FakeEntities({}))
    with pytest.raises(ValidationError):
        main._complete(1001, {"IsSuccessful": "maybe"}, ProcessQueueInput())


def test_queue_reports_a_completion_error_but_keeps_going(fake_sdk):
    class FlakyQueues(FakeQueues):
        def complete_transaction_item(self, transaction_key, *a, **k):
            if str(transaction_key) == "1001":
                request = httpx.Request("POST", "https://cloud.test/x")
                raise httpx.HTTPStatusError("503", request=request, response=httpx.Response(503, request=request))
            return super().complete_transaction_item(transaction_key, *a, **k)

    queues, _ = fake_sdk(FlakyQueues([tx("k1", "rec-001"), tx("k2", "rec-001")]), FakeEntities({"rec-001": NORTHWIND}))
    out = process_invoice_queue(ProcessQueueInput())
    assert out.processed == 2 and out.failed == 0
    assert len(out.errors) == 1 and "could not be marked Successful" in out.errors[0]
    assert [c[0] for c in queues.completed] == [1002]
