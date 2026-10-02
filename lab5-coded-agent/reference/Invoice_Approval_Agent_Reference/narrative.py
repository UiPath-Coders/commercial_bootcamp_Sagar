"""LLM narrative for gate 4 (READY_FOR_APPROVAL) invoices.

The LLM is reached through UiPath's LLM Gateway via ``UiPathChat`` from
``uipath-langchain`` (no API keys; usage is billed as Agent Units on the
tenant). The model is instantiated inside the function, never at module level,
so ``uip codedagent init`` can import this module without credentials.

``generate_narrative`` is ``@mockable`` so evaluations and pytest can replace
it. It never raises: if the gateway is unavailable, or
``AP_INVOICE_NARRATIVE_MODE=template`` is set, a deterministic template
narrative is produced and the ``source`` field says so. The deterministic
decision has already been made by the gates; the narrative only explains it.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from config import NARRATIVE_MODE_TEMPLATE, load_settings
from uipath.eval.mocks import mockable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an accounts-payable analyst preparing an approval package for a human approver. "
    "The invoice has already passed every deterministic control (the PO is matched, approval is "
    "required, and all approval evidence is present). Do not re-decide; do not invent facts. "
    "Write a concise narrative (3-5 sentences) covering: vendor and amount, PO match, the evidence "
    "on file (GL account, cost center, approver, receipt reference, payment terms), and vendor risk. "
    "List any risk flags the approver should glance at. Use only the data provided."
)


class ApprovalNarrative(BaseModel):
    """Structured output requested from the LLM."""

    summary: str = Field(description="3-5 sentence approval narrative for the approver")
    risk_flags: list[str] = Field(default_factory=list, description="Short risk flags, empty if none")
    confidence: str = Field(default="medium", description="low | medium | high")


def narrative_input(record: dict[str, Any]) -> dict[str, Any]:
    """The subset of record fields the LLM is allowed to see (no Ids, no tax Id)."""
    return {
        "VendorName": record.get("VendorName"),
        "InvoiceNumber": record.get("InvoiceNumber"),
        "InvoiceDate": record.get("InvoiceDate"),
        "DueDate": record.get("DueDate"),
        "PONumber": record.get("PONumber"),
        "TotalAmount": record.get("TotalAmount"),
        "Currency": record.get("Currency"),
        "POMatched": record.get("POMatched"),
        "ApprovalNeeded": record.get("ApprovalNeeded"),
        "GLAccount": record.get("GLAccount"),
        "CostCenter": record.get("CostCenter"),
        "Approver": record.get("Approver"),
        "PaymentTerms": record.get("PaymentTerms"),
        "VendorRiskScore": record.get("VendorRiskScore"),
        "ReceiptReference": record.get("ReceiptReference"),
        "InvoiceLineSummary": record.get("InvoiceLineSummary"),
    }


def template_narrative(facts: dict[str, Any], reason: str) -> dict[str, Any]:
    """Deterministic fallback used when the LLM is disabled or unreachable."""
    amount = facts.get("TotalAmount")
    currency = facts.get("Currency") or ""
    risk = str(facts.get("VendorRiskScore") or "unknown")
    flags: list[str] = []
    if risk.lower() not in ("low", ""):
        flags.append(f"Vendor risk score is {risk}")
    summary = (
        f"Invoice {facts.get('InvoiceNumber')} from {facts.get('VendorName')} for {amount} {currency} "
        f"is matched to purchase order {facts.get('PONumber')} and requires approval. "
        f"Evidence on file: GL account {facts.get('GLAccount')}, cost center {facts.get('CostCenter')}, "
        f"approver {facts.get('Approver')}, goods receipt {facts.get('ReceiptReference')}, "
        f"payment terms {facts.get('PaymentTerms')}. Vendor risk score: {risk}. "
        f"Lines: {facts.get('InvoiceLineSummary')}."
    ).strip()
    return {
        "summary": summary,
        "risk_flags": flags,
        "confidence": "high",
        "source": "template",
        "model": None,
        "reason": reason,
    }


def _llm_narrative(facts: dict[str, Any], model_name: str) -> dict[str, Any]:
    # Lazy imports: keep module import free of gateway/auth side effects.
    import json

    from langchain_core.messages import HumanMessage, SystemMessage
    from uipath_langchain.chat import UiPathChat

    llm = UiPathChat(model_name=model_name, temperature=0, max_tokens=600)
    structured = llm.with_structured_output(ApprovalNarrative)
    raw = structured.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="Invoice facts (JSON):\n" + json.dumps(facts, indent=2, default=str)),
        ]
    )
    # with_structured_output may return a dict or the model, depending on version.
    result = raw if isinstance(raw, ApprovalNarrative) else ApprovalNarrative.model_validate(raw)
    return {**result.model_dump(), "source": "llm", "model": model_name, "reason": None}


@mockable()
def generate_narrative(facts: dict[str, Any]) -> dict[str, Any]:
    """Produce the approval narrative for a READY_FOR_APPROVAL invoice.

    Returns a dict with ``summary``, ``risk_flags``, ``confidence``, ``source``
    (``llm`` or ``template``), ``model`` and ``reason``.
    """
    settings = load_settings()
    if settings.narrative_mode == NARRATIVE_MODE_TEMPLATE:
        return template_narrative(facts, reason="AP_INVOICE_NARRATIVE_MODE=template")
    try:
        return _llm_narrative(facts, settings.llm_model)
    except Exception as exc:  # noqa: BLE001 - the decision must still be written back
        logger.warning("LLM narrative failed (%s); falling back to template narrative", exc)
        return template_narrative(facts, reason=f"llm_error: {type(exc).__name__}: {exc}")
