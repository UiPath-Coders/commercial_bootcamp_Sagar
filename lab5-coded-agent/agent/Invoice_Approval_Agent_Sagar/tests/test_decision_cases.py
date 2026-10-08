"""Feed lab-assets/vendor-invoice/evaluations/decision-cases.json to the deterministic gates (no I/O, no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DECISION_CASES = PROJECT_ROOT.parents[1] / "lab-assets" / "vendor-invoice" / "evaluations" / "decision-cases.json"
sys.path.insert(0, str(PROJECT_ROOT))

from approval_gates import evaluate_gates  # noqa: E402

# decision-cases.json uses snake_case keys; the entity uses schema (PascalCase) names.
CASE_FIELD_MAP = {
    "invoice_reference": "InvoiceReference",
    "po_matched": "POMatched",
    "approval_needed": "ApprovalNeeded",
    "total_amount": "TotalAmount",
    "currency": "Currency",
    "gl_account": "GLAccount",
    "cost_center": "CostCenter",
    "approver": "Approver",
    "payment_terms": "PaymentTerms",
    "vendor_risk_score": "VendorRiskScore",
    "receipt_reference": "ReceiptReference",
    "invoice_line_summary": "InvoiceLineSummary",
}
# How the uip df CLI re-cases the same fields.
CLI_CASING = {"POMatched": "PoMatched", "GLAccount": "GlAccount"}

CASES = json.loads(DECISION_CASES.read_text(encoding="utf-8"))


def to_record(invoice_data: dict, casing: dict | None = None) -> dict:
    record = {CASE_FIELD_MAP[key]: value for key, value in invoice_data.items()}
    if casing:
        record = {casing.get(key, key): value for key, value in record.items()}
    return record


def actual(record: dict) -> dict:
    gate = evaluate_gates(record)
    return {
        "approval_evidence_state": gate.approval_evidence_state,
        "missing_approval_fields": list(gate.missing_approval_fields),
        "recommendation": gate.recommendation,
        "invoice_lifecycle_state": gate.invoice_lifecycle_state,
    }


def expected(case: dict) -> dict:
    return {k: v for k, v in case["expected"].items() if k != "invoice_reference"}


def test_dataset_has_six_cases():
    assert len(CASES) == 6


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["expected"]["invoice_reference"])
def test_decision_case(case):
    assert actual(to_record(case["invoice_data"])) == expected(case)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["expected"]["invoice_reference"] + "-cli-casing")
def test_decision_case_with_cli_casing(case):
    assert actual(to_record(case["invoice_data"], CLI_CASING)) == expected(case)
