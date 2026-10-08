"""Invoice_Approval_Agent_Sagar - Lab 5 LangGraph coded agent.

Input : {"recordId": "<AP_Invoice_Sagar record Id>"}
Reads : that one tenant-scoped record (UiPath Python SDK, no folder)
Guard : already prepared (AUTO_APPROVED / READY_FOR_APPROVAL + package) or decided
        (APPROVED / REJECTED / POSTED) -> return the stored result, no LLM, no write
Gates : four deterministic gates, in order, before any LLM call
LLM   : only for a new gate-4 (READY_FOR_APPROVAL) package narrative
Writes: ApprovalEvidenceState, MissingApprovalFields, AgentRecommendation,
        ApprovalPackageJson, AgentProcessedAt, InvoiceLifecycleState to the same record

Graph:
    START -> load_record -+-> evaluate_gates -+-> write_narrative -> write_back -> finish -> END
                          |                   +----------------------^
                          +-> finish   (error or retry guard)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from approval_gates import GateResult, check_retry_guard, evaluate_gates, format_missing_fields
from config import AGENT_NAME, PACKAGE_VERSION, load_settings
from data_fabric import RecordNotFoundError, read_invoice_record, write_agent_outputs
from narrative import generate_narrative, narrative_facts

# At INFO, httpx logs full request URLs; keep it quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Typed contract (entry-points.json is generated from these by `uip codedagent init`)
# --------------------------------------------------------------------------- #
class GraphInput(BaseModel):
    recordId: str = Field(description="Data Fabric Id of the AP_Invoice_Sagar record to evaluate")


class GraphOutput(BaseModel):
    recordId: str = Field(description="The same record Id that was read (and updated)")
    approvalEvidenceState: Optional[str] = Field(default=None, description="NOT_EVALUATED | NOT_REQUIRED | INCOMPLETE | COMPLETE")
    missingApprovalFields: list[str] = Field(default_factory=list, description="Empty required approval inputs (gate 3)")
    recommendation: Optional[str] = Field(default=None, description="HOLD_PO_MISMATCH | AUTO_APPROVED | NEEDS_AP_REVIEW | READY_FOR_APPROVAL")
    invoiceLifecycleState: Optional[str] = Field(default=None, description="InvoiceLifecycleState on the record after this run")
    wasAlreadyPrepared: bool = Field(default=False, description="True when the retry guard returned the stored result without reprocessing")
    errorType: Optional[str] = Field(default=None, description="INVALID_INPUT | RECORD_NOT_FOUND | READ_FAILED | WRITE_FAILED, or null")
    errorMessage: Optional[str] = Field(default=None, description="Error detail, or null")


class GraphState(BaseModel):
    recordId: str
    # Sanitised record: schema names only, never VendorTaxId or ApprovalPackageJson.
    record: Optional[dict[str, Any]] = None
    hasExistingPackage: bool = False
    decision: Optional[dict[str, Any]] = None
    narrative: Optional[dict[str, Any]] = None
    # outputs
    approvalEvidenceState: Optional[str] = None
    missingApprovalFields: list[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    invoiceLifecycleState: Optional[str] = None
    wasAlreadyPrepared: bool = False
    errorType: Optional[str] = None
    errorMessage: Optional[str] = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_approval_package(record: dict[str, Any], gate: GateResult, narrative: Optional[dict[str, Any]], processed_at: str) -> dict[str, Any]:
    """Structured package stored in ApprovalPackageJson. No tax Id."""
    return {
        "version": PACKAGE_VERSION,
        "agent": AGENT_NAME,
        "entity": load_settings().entity_name,
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
        "poMatch": {"poMatched": record.get("POMatched"), "approvalNeeded": record.get("ApprovalNeeded")},
        "evidence": {
            "glAccount": record.get("GLAccount"),
            "costCenter": record.get("CostCenter"),
            "approver": record.get("Approver"),
            "paymentTerms": record.get("PaymentTerms"),
            "vendorRiskScore": record.get("VendorRiskScore"),
            "receiptReference": record.get("ReceiptReference"),
            "invoiceLineSummary": record.get("InvoiceLineSummary"),
        },
        "gates": [dict(step) for step in gate.gate_trace],
        "decision": {
            "firedGate": gate.fired_gate,
            "approvalEvidenceState": gate.approval_evidence_state,
            "missingApprovalFields": list(gate.missing_approval_fields),
            "agentRecommendation": gate.recommendation,
            "invoiceLifecycleState": gate.invoice_lifecycle_state,
        },
        "narrative": narrative,
    }


def agent_output_fields(gate: GateResult, package: dict[str, Any], processed_at: str) -> dict[str, Any]:
    """Exactly the six fields the agent writes, keyed by schema name."""
    return {
        "ApprovalEvidenceState": gate.approval_evidence_state,
        "MissingApprovalFields": format_missing_fields(gate.missing_approval_fields),
        "AgentRecommendation": gate.recommendation,
        "ApprovalPackageJson": json.dumps(package, default=str),
        "AgentProcessedAt": processed_at,
        "InvoiceLifecycleState": gate.invoice_lifecycle_state,
    }


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #
async def load_record(state: GraphState) -> dict[str, Any]:
    record_id = (state.recordId or "").strip()
    if not record_id:
        return {"errorType": "INVALID_INPUT", "errorMessage": "recordId is required"}
    try:
        result = read_invoice_record(record_id)
    except RecordNotFoundError as exc:
        return {"errorType": "RECORD_NOT_FOUND", "errorMessage": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"errorType": "READ_FAILED", "errorMessage": f"{type(exc).__name__}: {str(exc)[:300]}"}

    record = {**result["record"], "Id": record_id}
    update: dict[str, Any] = {"record": record, "hasExistingPackage": bool(result["has_existing_package"])}

    guard = check_retry_guard(record, update["hasExistingPackage"])
    if guard is not None:
        update.update(
            wasAlreadyPrepared=True,
            approvalEvidenceState=guard.approval_evidence_state,
            missingApprovalFields=list(guard.missing_approval_fields),
            recommendation=guard.recommendation,
            invoiceLifecycleState=guard.invoice_lifecycle_state,
        )
    return update


def route_after_load(state: GraphState) -> Literal["evaluate_gates", "finish"]:
    return "finish" if state.errorType or state.wasAlreadyPrepared else "evaluate_gates"


async def run_gates(state: GraphState) -> dict[str, Any]:
    gate = evaluate_gates(state.record or {})
    return {"decision": gate.to_dict()}


def route_after_gates(state: GraphState) -> Literal["write_narrative", "write_back"]:
    return "write_narrative" if state.decision and state.decision["fired_gate"] == 4 else "write_back"


async def write_narrative(state: GraphState) -> dict[str, Any]:
    return {"narrative": generate_narrative(narrative_facts(state.record or {}))}


async def write_back(state: GraphState) -> dict[str, Any]:
    gate = GateResult.from_dict(state.decision or {})
    processed_at = utc_now_iso()
    package = build_approval_package(state.record or {}, gate, state.narrative, processed_at)
    outputs = {
        "approvalEvidenceState": gate.approval_evidence_state,
        "missingApprovalFields": list(gate.missing_approval_fields),
        "recommendation": gate.recommendation,
        "invoiceLifecycleState": gate.invoice_lifecycle_state,
    }
    try:
        write_agent_outputs(state.recordId.strip(), agent_output_fields(gate, package, processed_at))
    except Exception as exc:  # noqa: BLE001
        # Nothing was written: report the record's unchanged lifecycle state.
        outputs["invoiceLifecycleState"] = (state.record or {}).get("InvoiceLifecycleState")
        outputs.update(errorType="WRITE_FAILED", errorMessage=f"{type(exc).__name__}: {str(exc)[:300]}")
    return outputs


async def finish(state: GraphState) -> GraphOutput:
    # The runtime captures the last node's delta as the output, so return every field here.
    return GraphOutput(
        recordId=state.recordId,
        approvalEvidenceState=state.approvalEvidenceState,
        missingApprovalFields=list(state.missingApprovalFields),
        recommendation=state.recommendation,
        invoiceLifecycleState=state.invoiceLifecycleState,
        wasAlreadyPrepared=state.wasAlreadyPrepared,
        errorType=state.errorType,
        errorMessage=state.errorMessage,
    )


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("load_record", load_record)
builder.add_node("evaluate_gates", run_gates)
builder.add_node("write_narrative", write_narrative)
builder.add_node("write_back", write_back)
builder.add_node("finish", finish)

builder.add_edge(START, "load_record")
builder.add_conditional_edges("load_record", route_after_load, ["evaluate_gates", "finish"])
builder.add_conditional_edges("evaluate_gates", route_after_gates, ["write_narrative", "write_back"])
builder.add_edge("write_narrative", "write_back")
builder.add_edge("write_back", "finish")
builder.add_edge("finish", END)

graph = builder.compile()
