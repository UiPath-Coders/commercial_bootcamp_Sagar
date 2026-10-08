"""Deterministic core of Invoice_Approval_Agent_Sagar.

Pure functions only: no I/O, no LLM. They take one AP_Invoice_Sagar record (a
mapping keyed by field name, any casing) and decide:

* the retry guard - whether the record was already prepared or decided, and
* gates 1-4, evaluated in order and stopping at the first one that fires:

| # | Condition                                   | Evidence      | Recommendation / lifecycle |
|---|---------------------------------------------|---------------|----------------------------|
| 1 | POMatched false                             | NOT_EVALUATED | HOLD_PO_MISMATCH           |
| 2 | ApprovalNeeded false                        | NOT_REQUIRED  | AUTO_APPROVED              |
| 3 | GLAccount/CostCenter/Approver/ReceiptRef empty | INCOMPLETE | NEEDS_AP_REVIEW            |
| 4 | otherwise                                   | COMPLETE      | READY_FOR_APPROVAL         |

Only gate 4 leads to an LLM call, and that call happens in main.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

# Gate 3 required inputs, in the order MissingApprovalFields reports them.
REQUIRED_APPROVAL_INPUTS: tuple[str, ...] = ("GLAccount", "CostCenter", "Approver", "ReceiptReference")

APPROVAL_INPUT_FIELDS: tuple[str, ...] = (
    "GLAccount",
    "CostCenter",
    "Approver",
    "PaymentTerms",
    "VendorRiskScore",
    "ReceiptReference",
    "InvoiceLineSummary",
)

# ApprovalEvidenceState
NOT_EVALUATED = "NOT_EVALUATED"
NOT_REQUIRED = "NOT_REQUIRED"
INCOMPLETE = "INCOMPLETE"
COMPLETE = "COMPLETE"

# AgentRecommendation / InvoiceLifecycleState
HOLD_PO_MISMATCH = "HOLD_PO_MISMATCH"
AUTO_APPROVED = "AUTO_APPROVED"
NEEDS_AP_REVIEW = "NEEDS_AP_REVIEW"
READY_FOR_APPROVAL = "READY_FOR_APPROVAL"

# Lifecycle states set downstream (Lab 6 reviewer, Lab 4 posting). Never downgraded.
APPROVED = "APPROVED"
REJECTED = "REJECTED"
POSTED = "POSTED"

FINAL_STATES = frozenset({APPROVED, REJECTED, POSTED})
PREPARED_STATES = frozenset({AUTO_APPROVED, READY_FOR_APPROVAL}) | FINAL_STATES

_TRUE_STRINGS = {"true", "1", "yes", "y", "t"}
_FALSE_STRINGS = {"false", "0", "no", "n", "f", ""}


def get_field(record: Mapping[str, Any], name: str) -> Any:
    """Read a field case-insensitively (the uip df CLI prints PoMatched, the SDK POMatched)."""
    if name in record:
        return record[name]
    wanted = name.lower()
    for key, value in record.items():
        if key.lower() == wanted:
            return value
    return None


def as_bool(value: Any, default: bool) -> bool:
    """Normalise a Data Fabric Boolean that may arrive as bool, str, int or None."""
    if value is None:
        return default
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
    return value is None or (isinstance(value, str) and value.strip() == "")


def parse_missing_fields(value: Any) -> list[str]:
    """MissingApprovalFields is stored as comma-separated text on the record."""
    if is_empty(value):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def format_missing_fields(missing: tuple[str, ...] | list[str]) -> str:
    return ", ".join(missing)


@dataclass(frozen=True)
class GateResult:
    approval_evidence_state: str
    missing_approval_fields: tuple[str, ...]
    recommendation: str
    invoice_lifecycle_state: str
    fired_gate: int
    gate_trace: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def requires_narrative(self) -> bool:
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

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GateResult":
        return cls(
            approval_evidence_state=data["approval_evidence_state"],
            missing_approval_fields=tuple(data["missing_approval_fields"]),
            recommendation=data["recommendation"],
            invoice_lifecycle_state=data["invoice_lifecycle_state"],
            fired_gate=data["fired_gate"],
            gate_trace=tuple(data.get("gate_trace", [])),
        )


@dataclass(frozen=True)
class GuardResult:
    """Retry-guard outcome: skip processing and return the record's existing result."""

    reason: str
    approval_evidence_state: Optional[str]
    missing_approval_fields: tuple[str, ...]
    recommendation: Optional[str]
    invoice_lifecycle_state: str


def check_retry_guard(record: Mapping[str, Any], has_existing_package: bool) -> Optional[GuardResult]:
    """Return a GuardResult when the record must not be (re)processed, else None.

    * APPROVED / REJECTED / POSTED are never downgraded, with or without a package.
    * AUTO_APPROVED / READY_FOR_APPROVAL with a non-empty ApprovalPackageJson were
      already prepared: return the stored result, no LLM call, no write.
    """
    lifecycle = (get_field(record, "InvoiceLifecycleState") or "").strip().upper()
    if lifecycle in FINAL_STATES:
        reason = "final_state"
    elif lifecycle in PREPARED_STATES and has_existing_package:
        reason = "already_prepared"
    else:
        return None
    return GuardResult(
        reason=reason,
        approval_evidence_state=get_field(record, "ApprovalEvidenceState") or None,
        missing_approval_fields=tuple(parse_missing_fields(get_field(record, "MissingApprovalFields"))),
        recommendation=get_field(record, "AgentRecommendation") or None,
        invoice_lifecycle_state=lifecycle,
    )


def missing_required_inputs(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(name for name in REQUIRED_APPROVAL_INPUTS if is_empty(get_field(record, name)))


def evaluate_gates(record: Mapping[str, Any]) -> GateResult:
    """Run gates 1-4 in order against one record and stop at the first that fires.

    A missing POMatched counts as false (hold, never auto-approve). A missing
    ApprovalNeeded counts as true, as in Lab 3 get_invoice_status.
    """
    trace: list[dict[str, Any]] = []

    raw_po = get_field(record, "POMatched")
    po_matched = as_bool(raw_po, default=False)
    trace.append({"gate": 1, "check": "POMatched == true", "value": raw_po, "passed": po_matched})
    if not po_matched:
        return GateResult(NOT_EVALUATED, (), HOLD_PO_MISMATCH, HOLD_PO_MISMATCH, 1, tuple(trace))

    raw_needed = get_field(record, "ApprovalNeeded")
    approval_needed = as_bool(raw_needed, default=True)
    trace.append({"gate": 2, "check": "ApprovalNeeded == true (unset counts as true)", "value": raw_needed, "passed": approval_needed})
    if not approval_needed:
        return GateResult(NOT_REQUIRED, (), AUTO_APPROVED, AUTO_APPROVED, 2, tuple(trace))

    missing = missing_required_inputs(record)
    trace.append({"gate": 3, "check": "required approval inputs present", "missing": list(missing), "passed": not missing})
    if missing:
        return GateResult(INCOMPLETE, missing, NEEDS_AP_REVIEW, NEEDS_AP_REVIEW, 3, tuple(trace))

    trace.append({"gate": 4, "check": "all checks passed", "passed": True})
    return GateResult(COMPLETE, (), READY_FOR_APPROVAL, READY_FOR_APPROVAL, 4, tuple(trace))
