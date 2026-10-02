"""Deterministic core of the Lab 5 approval agent.

This module is pure: it takes one ``AP_Invoice_<user_name>`` record (a plain
``dict`` keyed by the Data Fabric system field names) and returns a
``GateResult``. It performs no I/O and never calls an LLM, so it can be unit
tested against ``lab-assets/vendor-invoice/evaluations/decision-cases.json``
without a tenant.

The four gates come from ``bootcamp-site/docs/commercial-process.md``
(section "Lab 5 deterministic gates") and are evaluated in order, stopping at
the first one that fires:

| # | Condition                              | Evidence      | Recommendation / lifecycle |
|---|----------------------------------------|---------------|----------------------------|
| 1 | POMatched == false                     | NOT_EVALUATED | HOLD_PO_MISMATCH           |
| 2 | ApprovalNeeded == false (explicit)     | NOT_REQUIRED  | AUTO_APPROVED              |
| 3 | any required approval input is empty   | INCOMPLETE    | NEEDS_AP_REVIEW            |
| 4 | all checks pass                        | COMPLETE      | READY_FOR_APPROVAL         |

Only gate 4 asks the LLM for a narrative; that happens in ``main.py``, not here.

An unset (``None``) ApprovalNeeded means "approval needed", as in Lab 3
``get_invoice_status``: gate 2 fires only on an explicit false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Approval inputs that gate 3 requires. Order matters: MissingApprovalFields is
# reported in this order (it matches the expected outputs in decision-cases.json).
REQUIRED_APPROVAL_INPUTS: tuple[str, ...] = (
    "GLAccount",
    "CostCenter",
    "Approver",
    "ReceiptReference",
)

# All seven Day 2 approval inputs (the four required ones plus context fields).
APPROVAL_INPUT_FIELDS: tuple[str, ...] = (
    "GLAccount",
    "CostCenter",
    "Approver",
    "PaymentTerms",
    "VendorRiskScore",
    "ReceiptReference",
    "InvoiceLineSummary",
)

# ApprovalEvidenceState values
NOT_EVALUATED = "NOT_EVALUATED"
NOT_REQUIRED = "NOT_REQUIRED"
INCOMPLETE = "INCOMPLETE"
COMPLETE = "COMPLETE"

# AgentRecommendation / InvoiceLifecycleState values written by this agent
HOLD_PO_MISMATCH = "HOLD_PO_MISMATCH"
AUTO_APPROVED = "AUTO_APPROVED"
NEEDS_AP_REVIEW = "NEEDS_AP_REVIEW"
READY_FOR_APPROVAL = "READY_FOR_APPROVAL"

_TRUE_STRINGS = {"true", "1", "yes", "y", "t"}
_FALSE_STRINGS = {"false", "0", "no", "n", "f", ""}


@dataclass(frozen=True)
class GateResult:
    """Outcome of the deterministic gate evaluation for one record."""

    approval_evidence_state: str
    missing_approval_fields: tuple[str, ...]
    recommendation: str
    invoice_lifecycle_state: str
    fired_gate: int
    gate_trace: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def requires_narrative(self) -> bool:
        """True only for gate 4 - the single case where the LLM is consulted."""
        return self.fired_gate == 4

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_evidence_state": self.approval_evidence_state,
            "missing_approval_fields": list(self.missing_approval_fields),
            "recommendation": self.recommendation,
            "invoice_lifecycle_state": self.invoice_lifecycle_state,
            "fired_gate": self.fired_gate,
            "gate_trace": [dict(step) for step in self.gate_trace],
        }


def as_bool(value: Any) -> bool:
    """Normalise a Data Fabric Boolean that may arrive as bool, str, int or None.

    ``None`` (field never written, e.g. Lab 3 did not run) is treated as
    ``False`` so that a record without a real PO-match result is held rather
    than auto-approved.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in _TRUE_STRINGS:
        return True
    if text in _FALSE_STRINGS:
        return False
    raise ValueError(f"Cannot interpret {value!r} as a boolean")


def is_empty(value: Any) -> bool:
    """A required approval input counts as empty when it is None or blank."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def missing_required_inputs(record: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the required approval inputs that are empty, in canonical order."""
    return tuple(name for name in REQUIRED_APPROVAL_INPUTS if is_empty(record.get(name)))


def evaluate_gates(record: Mapping[str, Any]) -> GateResult:
    """Run gates 1-4 in order against one AP_Invoice record and stop at the first hit.

    Args:
        record: the Data Fabric record as a mapping keyed by system field name
            (``POMatched``, ``ApprovalNeeded``, ``GLAccount`` ...). Extra keys
            are ignored; missing keys are treated as empty / false, except
            ApprovalNeeded, where a missing value means approval is needed.

    Returns:
        GateResult with the three state values, the missing-field list and a
        gate-by-gate trace suitable for the approval package.
    """
    trace: list[dict[str, Any]] = []

    # Gate 1 - PO matched?
    po_matched = as_bool(record.get("POMatched"))
    trace.append({"gate": 1, "check": "POMatched == true", "value": record.get("POMatched"), "passed": po_matched})
    if not po_matched:
        return GateResult(
            approval_evidence_state=NOT_EVALUATED,
            missing_approval_fields=(),
            recommendation=HOLD_PO_MISMATCH,
            invoice_lifecycle_state=HOLD_PO_MISMATCH,
            fired_gate=1,
            gate_trace=tuple(trace),
        )

    # Gate 2 - approval needed at all? Unset (None) means "approval needed"
    # (consistent with Lab 3 get_invoice_status); only an explicit false auto-approves.
    raw_approval_needed = record.get("ApprovalNeeded")
    approval_needed = True if raw_approval_needed is None else as_bool(raw_approval_needed)
    trace.append({"gate": 2, "check": "ApprovalNeeded != false (unset counts as true)", "value": raw_approval_needed, "passed": approval_needed})
    if not approval_needed:
        return GateResult(
            approval_evidence_state=NOT_REQUIRED,
            missing_approval_fields=(),
            recommendation=AUTO_APPROVED,
            invoice_lifecycle_state=AUTO_APPROVED,
            fired_gate=2,
            gate_trace=tuple(trace),
        )

    # Gate 3 - is the approval evidence complete?
    missing = missing_required_inputs(record)
    trace.append({"gate": 3, "check": "required approval inputs present", "missing": list(missing), "passed": not missing})
    if missing:
        return GateResult(
            approval_evidence_state=INCOMPLETE,
            missing_approval_fields=missing,
            recommendation=NEEDS_AP_REVIEW,
            invoice_lifecycle_state=NEEDS_AP_REVIEW,
            fired_gate=3,
            gate_trace=tuple(trace),
        )

    # Gate 4 - everything passed; the LLM narrative is generated by the caller.
    trace.append({"gate": 4, "check": "all checks passed", "passed": True})
    return GateResult(
        approval_evidence_state=COMPLETE,
        missing_approval_fields=(),
        recommendation=READY_FOR_APPROVAL,
        invoice_lifecycle_state=READY_FOR_APPROVAL,
        fired_gate=4,
        gate_trace=tuple(trace),
    )


def format_missing_fields(missing: tuple[str, ...] | list[str]) -> str:
    """Serialise MissingApprovalFields for the Text field on the record.

    Comma-separated so the Lab 6 reviewer app can show it verbatim; empty string
    when nothing is missing.
    """
    return ", ".join(missing)
