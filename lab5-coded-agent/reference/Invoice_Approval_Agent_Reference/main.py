"""Invoice_Approval_Agent_Reference - Lab 5 reference solution (LangGraph coded agent).

Build Approval Package step of the Invoice-to-Pay process (Office of the CFO).

Input : {"recordId": "<AP_Invoice record Id>"}  (optional "entityName" override)
Reads : the AP_Invoice_<user_name> record through the UiPath Python SDK (tenant scope)
Gates : approval_gates.evaluate_gates - four deterministic gates, in order, BEFORE any LLM call
LLM   : only for gate 4 (READY_FOR_APPROVAL), to write the narrative inside ApprovalPackageJson
Writes: ApprovalEvidenceState, MissingApprovalFields, AgentRecommendation, ApprovalPackageJson,
        AgentProcessedAt, InvoiceLifecycleState back to the SAME record. No second entity, no Status field.

Graph:
    START -> load_record -> evaluate_gates -+-> write_narrative -> write_back -> END   (gate 4 only)
                                            +----------------------^                   (gates 1-3)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from approval_gates import GateResult, evaluate_gates, format_missing_fields
from config import AGENT_NAME, PACKAGE_VERSION, load_settings
from data_fabric import describe_backend, read_invoice_record, write_agent_outputs
from narrative import generate_narrative, narrative_input


# --------------------------------------------------------------------------- #
# Typed contract (becomes entry-points.json via `uip codedagent init`)
# --------------------------------------------------------------------------- #
class GraphInput(BaseModel):
    recordId: str = Field(description="Data Fabric Id of the AP_Invoice record to evaluate")
    entityName: Optional[str] = Field(
        default=None,
        description="Optional override of the entity name (default: AP_INVOICE_ENTITY_NAME env, e.g. AP_Invoice_<user_name>)",
    )


class GraphOutput(BaseModel):
    record_id: str = Field(description="The same record Id that was read and updated")
    invoice_reference: Optional[str] = Field(default=None, description="InvoiceNumber of the record (training label only)")
    approval_evidence_state: str = Field(description="NOT_EVALUATED | NOT_REQUIRED | INCOMPLETE | COMPLETE")
    missing_approval_fields: list[str] = Field(default_factory=list, description="Empty required approval inputs")
    recommendation: str = Field(description="HOLD_PO_MISMATCH | AUTO_APPROVED | NEEDS_AP_REVIEW | READY_FOR_APPROVAL")
    invoice_lifecycle_state: str = Field(description="Lifecycle state written to InvoiceLifecycleState")
    agent_processed_at: str = Field(description="UTC ISO-8601 timestamp written to AgentProcessedAt")
    narrative_generated: bool = Field(description="True only when gate 4 fired and a narrative was produced")


class GraphState(BaseModel):
    recordId: str
    entityName: Optional[str] = None
    record: Optional[dict[str, Any]] = None
    decision: Optional[dict[str, Any]] = None
    narrative: Optional[dict[str, Any]] = None
    # output fields (populated by write_back)
    record_id: Optional[str] = None
    invoice_reference: Optional[str] = None
    approval_evidence_state: Optional[str] = None
    missing_approval_fields: list[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    invoice_lifecycle_state: Optional[str] = None
    agent_processed_at: Optional[str] = None
    narrative_generated: bool = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_approval_package(
    record: dict[str, Any],
    gate_result: GateResult,
    narrative: Optional[dict[str, Any]],
    processed_at: str,
    entity_name: str,
) -> dict[str, Any]:
    """The structured approval package stored in ApprovalPackageJson (narrative only for gate 4)."""
    return {
        "version": PACKAGE_VERSION,
        "agent": AGENT_NAME,
        "entity": entity_name,
        "recordId": record.get("Id"),
        "processedAt": processed_at,
        "invoice": {
            "vendorName": record.get("VendorName"),
            "invoiceNumber": record.get("InvoiceNumber"),
            "invoiceDate": record.get("InvoiceDate"),
            "dueDate": record.get("DueDate"),
            "poNumber": record.get("PONumber"),
            "totalAmount": record.get("TotalAmount"),
            "currency": record.get("Currency"),
        },
        "poMatch": {
            "poMatched": record.get("POMatched"),
            "approvalNeeded": record.get("ApprovalNeeded"),
        },
        "evidence": {
            "glAccount": record.get("GLAccount"),
            "costCenter": record.get("CostCenter"),
            "approver": record.get("Approver"),
            "paymentTerms": record.get("PaymentTerms"),
            "vendorRiskScore": record.get("VendorRiskScore"),
            "receiptReference": record.get("ReceiptReference"),
            "invoiceLineSummary": record.get("InvoiceLineSummary"),
        },
        "gates": [dict(step) for step in gate_result.gate_trace],
        "decision": {
            "firedGate": gate_result.fired_gate,
            "approvalEvidenceState": gate_result.approval_evidence_state,
            "missingApprovalFields": list(gate_result.missing_approval_fields),
            "agentRecommendation": gate_result.recommendation,
            "invoiceLifecycleState": gate_result.invoice_lifecycle_state,
        },
        "narrative": narrative,
    }


def agent_output_fields(gate_result: GateResult, package: dict[str, Any], processed_at: str) -> dict[str, Any]:
    """Exactly the six fields the agent writes back to the record."""
    return {
        "ApprovalEvidenceState": gate_result.approval_evidence_state,
        "MissingApprovalFields": format_missing_fields(gate_result.missing_approval_fields),
        "AgentRecommendation": gate_result.recommendation,
        "ApprovalPackageJson": json.dumps(package, default=str),
        "AgentProcessedAt": processed_at,
        "InvoiceLifecycleState": gate_result.invoice_lifecycle_state,
    }


# --------------------------------------------------------------------------- #
# Graph nodes
# --------------------------------------------------------------------------- #
async def load_record(state: GraphState) -> dict[str, Any]:
    settings = load_settings(state.entityName)
    record = read_invoice_record(settings.entity_name, state.recordId)
    if "Id" not in record:
        record = {**record, "Id": state.recordId}
    return {"record": record, "entityName": settings.entity_name}


async def run_gates(state: GraphState) -> dict[str, Any]:
    assert state.record is not None, "load_record must run first"
    result = evaluate_gates(state.record)
    return {"decision": result.to_dict()}


def route_after_gates(state: GraphState) -> Literal["write_narrative", "write_back"]:
    assert state.decision is not None
    return "write_narrative" if state.decision["fired_gate"] == 4 else "write_back"


async def write_narrative(state: GraphState) -> dict[str, Any]:
    assert state.record is not None
    facts = narrative_input(state.record)
    return {"narrative": generate_narrative(facts)}


async def write_back(state: GraphState) -> dict[str, Any]:
    assert state.record is not None and state.decision is not None
    gate_result = _gate_result_from_state(state.decision)
    processed_at = utc_now_iso()
    entity_name = state.entityName or load_settings().entity_name
    package = build_approval_package(state.record, gate_result, state.narrative, processed_at, entity_name)
    fields = agent_output_fields(gate_result, package, processed_at)
    write_agent_outputs(entity_name, state.recordId, fields)
    # The runtime captures the LAST node's delta as the output, so every output
    # field is returned here (not accumulated through reducers).
    return {
        "record_id": state.recordId,
        # InvoiceReference exists only on the AP-TRAIN evaluation records; live records carry InvoiceNumber.
        "invoice_reference": state.record.get("InvoiceReference") or state.record.get("InvoiceNumber"),
        "approval_evidence_state": gate_result.approval_evidence_state,
        "missing_approval_fields": list(gate_result.missing_approval_fields),
        "recommendation": gate_result.recommendation,
        "invoice_lifecycle_state": gate_result.invoice_lifecycle_state,
        "agent_processed_at": processed_at,
        "narrative_generated": state.narrative is not None,
    }


def _gate_result_from_state(decision: dict[str, Any]) -> GateResult:
    return GateResult(
        approval_evidence_state=decision["approval_evidence_state"],
        missing_approval_fields=tuple(decision["missing_approval_fields"]),
        recommendation=decision["recommendation"],
        invoice_lifecycle_state=decision["invoice_lifecycle_state"],
        fired_gate=decision["fired_gate"],
        gate_trace=tuple(decision.get("gate_trace", [])),
    )


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("load_record", load_record)
builder.add_node("evaluate_gates", run_gates)
builder.add_node("write_narrative", write_narrative)
builder.add_node("write_back", write_back)

builder.add_edge(START, "load_record")
builder.add_edge("load_record", "evaluate_gates")
builder.add_conditional_edges("evaluate_gates", route_after_gates, ["write_narrative", "write_back"])
builder.add_edge("write_narrative", "write_back")
builder.add_edge("write_back", END)

graph = builder.compile()

__all__ = ["graph", "GraphInput", "GraphOutput", "build_approval_package", "agent_output_fields", "describe_backend"]
