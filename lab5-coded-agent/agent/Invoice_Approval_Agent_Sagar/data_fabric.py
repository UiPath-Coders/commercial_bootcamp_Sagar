"""Data Fabric I/O for AP_Invoice_Sagar (UiPath Python SDK, tenant scope, no folder).

The SDK addresses records by entity Id, never by name. The configured entity
name is resolved once per process with `sdk.entities.retrieve_by_name` and
cached; AP_INVOICE_ENTITY_ID skips the lookup.

`read_invoice_record` returns the record sanitised for graph state: keys are
mapped case-insensitively onto the schema names below, VendorTaxId is never
included, and ApprovalPackageJson is reduced to a "has package" flag, because
`uip codedagent run` prints the full state after every node.
"""

from __future__ import annotations

from typing import Any

from uipath.eval.mocks import mockable

from config import load_settings

# Fields the agent may hold in graph state (schema names). VendorTaxId is deliberately absent.
STATE_FIELDS: tuple[str, ...] = (
    "Id",
    "VendorName",
    "InvoiceNumber",
    "InvoiceDate",
    "PONumber",
    "TotalAmount",
    "Currency",
    "DueDate",
    "POMatched",
    "ApprovalNeeded",
    "PostedToERP",
    "InvoiceLifecycleState",
    "GLAccount",
    "CostCenter",
    "Approver",
    "PaymentTerms",
    "VendorRiskScore",
    "ReceiptReference",
    "InvoiceLineSummary",
    "ApprovalEvidenceState",
    "MissingApprovalFields",
    "AgentRecommendation",
    "AgentProcessedAt",
)

# The six fields this agent owns on the record. Nothing else is ever written.
AGENT_OUTPUT_FIELDS: tuple[str, ...] = (
    "ApprovalEvidenceState",
    "MissingApprovalFields",
    "AgentRecommendation",
    "ApprovalPackageJson",
    "AgentProcessedAt",
    "InvoiceLifecycleState",
)

_STATE_FIELD_BY_LOWER = {name.lower(): name for name in STATE_FIELDS}
_entity_id_cache: dict[str, str] = {}


class RecordNotFoundError(LookupError):
    """The record Id does not exist in the entity."""


def _sdk():
    # Lazy: `uip codedagent init` imports this module without credentials.
    from uipath.platform import UiPath

    return UiPath()


def resolve_entity_id(sdk=None) -> str:
    settings = load_settings()
    if settings.entity_id:
        return settings.entity_id
    cached = _entity_id_cache.get(settings.entity_name)
    if cached:
        return cached
    sdk = sdk or _sdk()
    entity = sdk.entities.retrieve_by_name(settings.entity_name)  # tenant-scoped: no folder_key
    _entity_id_cache[settings.entity_name] = entity.id
    return entity.id


def sanitize_record(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Map keys case-insensitively to schema names and drop everything else.

    Returns (record, has_existing_package).
    """
    record: dict[str, Any] = {}
    has_package = False
    for key, value in raw.items():
        lower = key.lower()
        if lower == "approvalpackagejson":
            has_package = isinstance(value, str) and value.strip() != ""
            continue
        name = _STATE_FIELD_BY_LOWER.get(lower)
        if name is not None:
            record[name] = value
    return record, has_package


def _is_not_found(exc: Exception) -> bool:
    status = getattr(getattr(exc, "response", None), "status_code", None) or getattr(exc, "status_code", None)
    return status == 404 or "404" in str(exc)[:200]


@mockable()
def read_invoice_record(record_id: str) -> dict[str, Any]:
    """Read one record by Id. Returns {"record": {...sanitised...}, "has_existing_package": bool}."""
    sdk = _sdk()
    entity_id = resolve_entity_id(sdk)
    try:
        raw = sdk.entities.get_record(entity_id, record_id)
    except Exception as exc:  # noqa: BLE001
        if _is_not_found(exc):
            raise RecordNotFoundError(f"Record {record_id} not found in the configured entity") from None
        raise
    data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
    record, has_package = sanitize_record(data)
    return {"record": record, "has_existing_package": has_package}


@mockable()
def write_agent_outputs(record_id: str, fields: dict[str, Any]) -> bool:
    """Write the six agent output fields to the same record. The SDK response is not returned or logged."""
    unexpected = sorted(set(fields) - set(AGENT_OUTPUT_FIELDS))
    if unexpected:
        raise ValueError(f"Refusing to write non-agent fields to the record: {unexpected}")
    sdk = _sdk()
    entity_id = resolve_entity_id(sdk)
    # Single-record update_record fires Data Fabric triggers, unlike the batch call.
    sdk.entities.update_record(entity_id, record_id, fields)
    return True
