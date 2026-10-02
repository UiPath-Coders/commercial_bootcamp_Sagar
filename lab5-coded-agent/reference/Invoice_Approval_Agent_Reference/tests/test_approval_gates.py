"""Deterministic gates vs. every case in decision-cases.json and the seed CSV (no I/O, no LLM)."""

from __future__ import annotations

import pytest

from approval_gates import (
    AUTO_APPROVED,
    COMPLETE,
    HOLD_PO_MISMATCH,
    INCOMPLETE,
    NEEDS_AP_REVIEW,
    NOT_EVALUATED,
    NOT_REQUIRED,
    READY_FOR_APPROVAL,
    REQUIRED_APPROVAL_INPUTS,
    GateResult,
    as_bool,
    evaluate_gates,
    format_missing_fields,
    is_empty,
)
from conftest import DECISION_MATRIX, case_to_record, load_decision_cases, load_seed_rows

CASES = load_decision_cases()
SEEDS = load_seed_rows()


@pytest.mark.parametrize("case", CASES, ids=[c["expected"]["invoice_reference"] for c in CASES])
def test_decision_case_matches_expected(case):
    record = case_to_record(case["invoice_data"])
    expected = case["expected"]

    result = evaluate_gates(record)

    assert result.approval_evidence_state == expected["approval_evidence_state"]
    assert list(result.missing_approval_fields) == expected["missing_approval_fields"]
    assert result.recommendation == expected["recommendation"]
    assert result.invoice_lifecycle_state == expected["invoice_lifecycle_state"]


@pytest.mark.parametrize("row", SEEDS, ids=[r["InvoiceReference"] for r in SEEDS])
def test_seed_csv_row_matches_decision_matrix(row):
    """The seed CSV is what participants import as evaluation records; booleans arrive as 'True'/'False' text."""
    expected_recommendation, expected_missing = DECISION_MATRIX[row["InvoiceReference"]]

    result = evaluate_gates(row)

    assert result.recommendation == expected_recommendation
    assert result.invoice_lifecycle_state == expected_recommendation
    assert list(result.missing_approval_fields) == expected_missing


def test_seed_csv_and_decision_cases_cover_the_same_references():
    assert {r["InvoiceReference"] for r in SEEDS} == {c["expected"]["invoice_reference"] for c in CASES}
    assert set(DECISION_MATRIX) == {c["expected"]["invoice_reference"] for c in CASES}


def test_every_gate_path_is_exercised_by_the_dataset():
    fired = {evaluate_gates(case_to_record(c["invoice_data"])).fired_gate for c in CASES}
    assert fired == {1, 2, 3, 4}


class TestGateOrder:
    """Gates stop at the first hit, in the order 1 -> 2 -> 3 -> 4."""

    complete_evidence = {
        "GLAccount": "6120",
        "CostCenter": "CC-410",
        "Approver": "Jordan Example",
        "ReceiptReference": "GR-1",
    }

    def test_gate1_po_mismatch_wins_even_when_evidence_is_missing(self):
        result = evaluate_gates({"POMatched": False, "ApprovalNeeded": True})
        assert (result.fired_gate, result.approval_evidence_state) == (1, NOT_EVALUATED)
        assert result.recommendation == result.invoice_lifecycle_state == HOLD_PO_MISMATCH
        assert result.missing_approval_fields == ()

    def test_gate1_fires_when_po_matched_was_never_written(self):
        """A record Lab 3 never touched must be held, not auto-approved."""
        result = evaluate_gates({"ApprovalNeeded": False, **self.complete_evidence})
        assert result.fired_gate == 1

    def test_gate2_auto_approved_ignores_evidence(self):
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": False})
        assert (result.fired_gate, result.approval_evidence_state) == (2, NOT_REQUIRED)
        assert result.recommendation == result.invoice_lifecycle_state == AUTO_APPROVED

    def test_gate2_unset_approval_needed_means_approval_needed(self):
        """An unset ApprovalNeeded is not an explicit false: gate 2 must not auto-approve."""
        result = evaluate_gates({"POMatched": True})
        assert result.fired_gate == 3
        assert result.recommendation == result.invoice_lifecycle_state == NEEDS_AP_REVIEW
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": None, **self.complete_evidence})
        assert (result.fired_gate, result.approval_evidence_state) == (4, COMPLETE)
        assert result.recommendation == READY_FOR_APPROVAL

    def test_gate3_lists_missing_fields_in_canonical_order(self):
        result = evaluate_gates(
            {"POMatched": True, "ApprovalNeeded": True, "ReceiptReference": None, "Approver": "", "CostCenter": "   "}
        )
        assert (result.fired_gate, result.approval_evidence_state) == (3, INCOMPLETE)
        assert result.recommendation == result.invoice_lifecycle_state == NEEDS_AP_REVIEW
        assert list(result.missing_approval_fields) == ["GLAccount", "CostCenter", "Approver", "ReceiptReference"]
        assert list(result.missing_approval_fields) == list(REQUIRED_APPROVAL_INPUTS)

    def test_gate3_ignores_optional_context_fields(self):
        """PaymentTerms, VendorRiskScore and InvoiceLineSummary are context, not gate-3 requirements."""
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": True, **self.complete_evidence})
        assert result.fired_gate == 4

    def test_gate4_complete(self):
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": True, **self.complete_evidence})
        assert (result.fired_gate, result.approval_evidence_state) == (4, COMPLETE)
        assert result.recommendation == result.invoice_lifecycle_state == READY_FOR_APPROVAL
        assert result.missing_approval_fields == ()

    def test_only_gate4_requires_the_llm(self):
        for record, expect in [
            ({"POMatched": False}, False),
            ({"POMatched": True, "ApprovalNeeded": False}, False),
            ({"POMatched": True, "ApprovalNeeded": True}, False),
            ({"POMatched": True, "ApprovalNeeded": True, **self.complete_evidence}, True),
        ]:
            assert evaluate_gates(record).requires_narrative is expect

    def test_gate_trace_records_every_evaluated_gate(self):
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": True, **self.complete_evidence})
        assert [step["gate"] for step in result.gate_trace] == [1, 2, 3, 4]
        result = evaluate_gates({"POMatched": True, "ApprovalNeeded": False})
        assert [step["gate"] for step in result.gate_trace] == [1, 2]


class TestNormalisation:
    @pytest.mark.parametrize("value", [True, "true", "True", "TRUE", 1, "1", "yes"])
    def test_truthy(self, value):
        assert as_bool(value) is True

    @pytest.mark.parametrize("value", [False, "false", "False", 0, "0", "no", "", None])
    def test_falsy(self, value):
        assert as_bool(value) is False

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            as_bool("maybe")

    @pytest.mark.parametrize("value,expected", [(None, True), ("", True), ("  ", True), ("x", False), (0, False)])
    def test_is_empty(self, value, expected):
        assert is_empty(value) is expected

    def test_format_missing_fields(self):
        assert format_missing_fields(()) == ""
        assert format_missing_fields(("GLAccount", "Approver")) == "GLAccount, Approver"


def test_gate_result_is_immutable_and_serialisable():
    result = evaluate_gates({"POMatched": True, "ApprovalNeeded": False})
    assert isinstance(result, GateResult)
    with pytest.raises(AttributeError):
        result.recommendation = "x"  # type: ignore[misc]
    as_dict = result.to_dict()
    assert as_dict["recommendation"] == AUTO_APPROVED
    assert as_dict["missing_approval_fields"] == []
    assert isinstance(as_dict["gate_trace"], list)
