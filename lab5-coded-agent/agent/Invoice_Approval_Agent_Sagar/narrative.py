"""LLM approval narrative, used only for gate 4 (READY_FOR_APPROVAL).

The LLM is reached through the UiPath LLM Gateway (`UiPathChat`, no API keys).
The client is created inside the function, never at module level. If the call
fails, a deterministic template narrative is used and `source` says so: the
decision was already made by the gates; the narrative only explains it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from uipath.eval.mocks import mockable

from config import load_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an accounts-payable analyst preparing an approval package for a human approver. "
    "The invoice has already passed every deterministic control (PO matched, approval required, "
    "all approval evidence present). Do not re-decide and do not invent facts. Write a concise "
    "narrative of 3-5 sentences covering vendor and amount, the PO match, the evidence on file "
    "(GL account, cost center, approver, receipt reference, payment terms) and vendor risk. "
    "List any risk flags the approver should glance at. Use only the data provided."
)

# The only record fields the LLM may see (no Ids, no tax Id).
NARRATIVE_FIELDS: tuple[str, ...] = (
    "VendorName",
    "InvoiceNumber",
    "InvoiceDate",
    "DueDate",
    "PONumber",
    "TotalAmount",
    "Currency",
    "GLAccount",
    "CostCenter",
    "Approver",
    "PaymentTerms",
    "VendorRiskScore",
    "ReceiptReference",
    "InvoiceLineSummary",
)


class ApprovalNarrative(BaseModel):
    summary: str = Field(description="3-5 sentence approval narrative for the approver")
    risk_flags: list[str] = Field(default_factory=list, description="Short risk flags, empty if none")


def narrative_facts(record: dict[str, Any]) -> dict[str, Any]:
    return {name: record.get(name) for name in NARRATIVE_FIELDS}


def template_narrative(facts: dict[str, Any], reason: str) -> dict[str, Any]:
    risk = str(facts.get("VendorRiskScore") or "unknown")
    flags = [] if risk.lower() in ("low", "unknown") else [f"Vendor risk score is {risk}"]
    summary = (
        f"Invoice {facts.get('InvoiceNumber')} from {facts.get('VendorName')} for "
        f"{facts.get('TotalAmount')} {facts.get('Currency') or ''} is matched to purchase order "
        f"{facts.get('PONumber')} and requires approval. Evidence on file: GL account {facts.get('GLAccount')}, "
        f"cost center {facts.get('CostCenter')}, approver {facts.get('Approver')}, receipt "
        f"{facts.get('ReceiptReference')}, payment terms {facts.get('PaymentTerms')}. Vendor risk: {risk}."
    )
    return {"summary": summary, "risk_flags": flags, "source": "template", "model": None, "reason": reason}


def _llm_narrative(facts: dict[str, Any], model_name: str) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from uipath_langchain.chat import UiPathChat

    llm = UiPathChat(model=model_name, temperature=0, max_tokens=600)
    raw = llm.with_structured_output(ApprovalNarrative).invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="Invoice facts (JSON):\n" + json.dumps(facts, indent=2, default=str)),
        ]
    )
    result = raw if isinstance(raw, ApprovalNarrative) else ApprovalNarrative.model_validate(raw)
    return {**result.model_dump(), "source": "llm", "model": model_name, "reason": None}


@mockable()
def generate_narrative(facts: dict[str, Any]) -> dict[str, Any]:
    """Return {summary, risk_flags, source ('llm' | 'template'), model, reason}. Never raises."""
    model_name = load_settings().llm_model
    try:
        return _llm_narrative(facts, model_name)
    except Exception as exc:  # noqa: BLE001 - the gate decision must still be written back
        logger.warning("LLM narrative failed (%s); using template narrative", type(exc).__name__)
        return template_narrative(facts, reason=f"llm_error: {type(exc).__name__}")
