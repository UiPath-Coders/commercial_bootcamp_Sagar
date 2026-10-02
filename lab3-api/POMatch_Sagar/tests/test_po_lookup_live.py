"""po_lookup against the LIVE mock ERP (commercial_bootcamp_lab_assets/mock-erp, node server.mjs).

The expected outcomes are the table in commercial_bootcamp_lab_assets/README.md, which the fixture
mock-erp/data/purchase-orders.json implements.
"""

from __future__ import annotations

import pytest

import main
from main import POLookupInput, po_lookup

# (invoice, vendor, PO, total, expected POMatched, expected ApprovalNeeded, match reason)
LAB_INVOICES = [
    ("001", "Northwind Office Supplies", "PO-2026-0431", 4155.40, True, False, "MATCHED"),
    ("002", "Contoso Logistics", "PO-2026-0447", 12740.00, True, True, "MATCHED"),
    ("003", "Ableton Fabrication", "PO-2026-0452", 4026.88, True, False, "MATCHED"),
    ("004", "Meridian Cloud Services", "PO-2026-0399", 16980.00, True, True, "MATCHED"),
    ("005", "Blue Harbor Catering", "PO-2026-0461", 2954.00, False, True, "VENDOR_INACTIVE"),
    ("006", "Great Lakes Steel Supply", "PO-2026-0470", 17988.20, False, True, "OUTSIDE_TOLERANCE"),
    ("007", "Liberty Print & Signage", "PO-2026-0476", 4946.40, True, False, "MATCHED"),
    ("008", "Summit Facilities Group", "PO-2026-0468", 3699.26, True, False, "MATCHED"),
    ("009", "Vertex Analytics", "PO-2026-0405", 22700.00, True, True, "MATCHED"),
    ("010", "Pacific Timber Company", "PO-2026-0489", 9902.58, False, True, "PO_NOT_FOUND"),
]


@pytest.fixture(autouse=True)
def point_at_live_erp(live_erp: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ERP_API_URL", live_erp)


@pytest.mark.parametrize(
    ("invoice", "vendor", "po_number", "total", "matched", "approval", "reason"),
    LAB_INVOICES,
    ids=[row[0] for row in LAB_INVOICES],
)
def test_all_ten_lab_invoices(invoice, vendor, po_number, total, matched, approval, reason):
    out = po_lookup(POLookupInput(vendor_name=vendor, po_number=po_number, invoice_total=total, currency="USD"))
    assert out.error_type == "", out.error_message
    assert out.error_message == ""
    assert out.po_matched is matched
    assert out.approval_required is approval
    assert out.match_reason == reason


def test_exactly_four_invoices_are_auto_approved():
    """The auto-approved path (matched AND not over threshold) is the process happy path."""
    auto = [
        row[0]
        for row in LAB_INVOICES
        if not po_lookup(POLookupInput(vendor_name=row[1], po_number=row[2], invoice_total=row[3])).approval_required
    ]
    assert auto == ["001", "003", "007", "008"]


def test_lab_step_4_sample_payload():
    """Lab 3 step 4, first run: the samplepolookup.md payload."""
    out = po_lookup(POLookupInput(vendor_name="Vertex Analytics Corp.", po_number="PO-2026-0405", invoice_total=22700, currency="USD"))
    assert out.model_dump() == {
        "po_matched": True,
        "approval_required": True,
        "open_amount": 22700.0,
        "match_reason": "MATCHED",
        "error_type": "",
        "error_message": "",
    }


def test_lab_step_4_unknown_po():
    """Lab 3 step 4, second run: an unknown PO returns found: false, so not matched, approval needed."""
    out = po_lookup(POLookupInput(vendor_name="Vertex Analytics Corp.", po_number="PO-0000-9999", invoice_total=22700, currency="USD"))
    assert out.po_matched is False
    assert out.approval_required is True
    assert out.open_amount == 0.0
    assert out.match_reason == "PO_NOT_FOUND"
    assert out.error_type == ""


def test_po_number_is_case_insensitive_at_the_erp():
    out = po_lookup(POLookupInput(vendor_name="Northwind Office Supplies", po_number="po-2026-0431", invoice_total=4155.40))
    assert out.po_matched is True


def test_live_erp_returns_400_without_po_number_and_the_function_guards_first():
    """The real server answers 400 when poNumber is missing; po_lookup refuses before the call."""
    import httpx

    response = httpx.post(f"{main.erp_api_url()}/api/po-lookup", json={"vendorName": "x"}, timeout=5)
    assert response.status_code == 400

    out = po_lookup(POLookupInput(vendor_name="x", po_number="   ", invoice_total=1))
    assert out.error_type == "INVALID_INPUT"
    assert out.po_matched is False and out.approval_required is True
