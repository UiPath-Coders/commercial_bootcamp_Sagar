"""Shared fixtures: load the Lab 5 dataset and map it onto Data Fabric field names."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAB_ASSETS = PROJECT_ROOT.parents[1] / "lab-assets" / "vendor-invoice"
DECISION_CASES = LAB_ASSETS / "evaluations" / "decision-cases.json"
SEED_CSV = LAB_ASSETS / "seeds" / "data-fabric-input.csv"
ENRICHMENT_CSV = LAB_ASSETS / "seeds" / "day2-approval-enrichment.csv"

# The agent modules live at the project root (flat layout required by langgraph.json).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# decision-cases.json uses snake_case keys; the entity uses PascalCase system names.
CASE_FIELD_MAP: dict[str, str] = {
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

# Expected outcome per AP-TRAIN reference, from lab-assets/vendor-invoice/README.md.
DECISION_MATRIX: dict[str, tuple[str, list[str]]] = {
    "AP-TRAIN-1001": ("READY_FOR_APPROVAL", []),
    "AP-TRAIN-1002": ("NEEDS_AP_REVIEW", ["ReceiptReference"]),
    "AP-TRAIN-1003": ("AUTO_APPROVED", []),
    "AP-TRAIN-1004": ("HOLD_PO_MISMATCH", []),
    "AP-TRAIN-1005": ("NEEDS_AP_REVIEW", ["GLAccount", "Approver"]),
    "AP-TRAIN-1006": ("READY_FOR_APPROVAL", []),
}


def case_to_record(invoice_data: dict[str, Any]) -> dict[str, Any]:
    """Turn one decision-case ``invoice_data`` block into an AP_Invoice-shaped record dict."""
    record = {CASE_FIELD_MAP[key]: value for key, value in invoice_data.items()}
    record["Id"] = f"rec-{invoice_data['invoice_reference'].lower()}"
    return record


def load_decision_cases() -> list[dict[str, Any]]:
    return json.loads(DECISION_CASES.read_text(encoding="utf-8"))


def load_seed_rows(path: Path = SEED_CSV) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    # CSV blanks are empty Data Fabric fields
    return [{k: (v if v != "" else None) for k, v in row.items()} for row in rows]


@pytest.fixture(scope="session")
def decision_cases() -> list[dict[str, Any]]:
    return load_decision_cases()


@pytest.fixture(scope="session")
def seed_rows() -> list[dict[str, Any]]:
    return load_seed_rows()


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch):
    """Never let a developer's .env leak into the tests; force template narrative unless a test overrides it."""
    for name in (
        "AP_INVOICE_ENTITY_NAME",
        "AP_INVOICE_ENTITY_ID",
        "AP_INVOICE_FIXTURE_FILE",
        "AP_INVOICE_FIXTURE_OUTPUT_DIR",
        "AP_INVOICE_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AP_INVOICE_NARRATIVE_MODE", "template")
    yield
