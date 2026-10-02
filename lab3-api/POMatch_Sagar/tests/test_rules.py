"""Pure business-rule tests: no HTTP, no SDK."""

from __future__ import annotations

import pytest

from main import APPROVAL_THRESHOLD, PO_TOLERANCE, evaluate_po, parse_po_response, MalformedErpResponse


def test_constants_match_the_spec():
    assert PO_TOLERANCE == 0.02
    assert APPROVAL_THRESHOLD == 10_000


@pytest.mark.parametrize(
    ("found", "active", "open_amount", "total", "matched", "approval", "reason"),
    [
        (True, True, 4200.0, 4155.40, True, False, "MATCHED"),  # Northwind: within 2%, under threshold
        (True, True, 12740.0, 12740.0, True, True, "MATCHED"),  # Contoso: exact, over threshold
        (True, False, 2954.0, 2954.0, False, True, "VENDOR_INACTIVE"),  # Blue Harbor
        (True, True, 16900.0, 17988.20, False, True, "OUTSIDE_TOLERANCE"),  # Great Lakes Steel
        (False, False, 0.0, 9902.58, False, True, "PO_NOT_FOUND"),  # Pacific Timber
    ],
)
def test_lab_paths(found, active, open_amount, total, matched, approval, reason):
    assert evaluate_po(found=found, vendor_active=active, open_amount=open_amount, invoice_total=total) == (
        matched,
        approval,
        reason,
    )


def test_tolerance_boundaries():
    # exactly 2% over and under still matches; a cent past it does not
    assert evaluate_po(found=True, vendor_active=True, open_amount=1000.0, invoice_total=1020.0)[0] is True
    assert evaluate_po(found=True, vendor_active=True, open_amount=1000.0, invoice_total=980.0)[0] is True
    assert evaluate_po(found=True, vendor_active=True, open_amount=1000.0, invoice_total=1020.01)[2] == "OUTSIDE_TOLERANCE"
    assert evaluate_po(found=True, vendor_active=True, open_amount=1000.0, invoice_total=979.99)[2] == "OUTSIDE_TOLERANCE"


def test_threshold_boundary():
    # 10,000 exactly is NOT over the threshold; 10,000.01 is
    assert evaluate_po(found=True, vendor_active=True, open_amount=10_000.0, invoice_total=10_000.0)[1] is False
    assert evaluate_po(found=True, vendor_active=True, open_amount=10_000.0, invoice_total=10_000.01)[1] is True


def test_unmatched_always_requires_approval_even_when_small():
    assert evaluate_po(found=False, vendor_active=True, open_amount=0.0, invoice_total=12.0)[1] is True
    assert evaluate_po(found=True, vendor_active=False, open_amount=12.0, invoice_total=12.0)[1] is True


def test_parse_po_response_accepts_the_documented_shape():
    po = parse_po_response({"po": {"found": True, "vendorActive": True, "openAmount": 22700.0, "currency": "USD"}})
    assert po == {"found": True, "vendor_active": True, "open_amount": 22700.0, "currency": "USD"}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"po": None},
        {"po": "found"},
        {"po": {}},
        {"po": {"found": "true", "vendorActive": True, "openAmount": 1}},
        {"po": {"found": True, "vendorActive": 1, "openAmount": 1}},
        {"po": {"found": True, "vendorActive": True, "openAmount": "22700"}},
        {"po": {"found": True, "vendorActive": True, "openAmount": True}},
        {"po": {"found": True, "vendorActive": True}},
    ],
)
def test_parse_po_response_rejects_malformed_bodies(payload):
    with pytest.raises(MalformedErpResponse):
        parse_po_response(payload)
