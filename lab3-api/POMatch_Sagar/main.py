"""POMatch_Sagar — Lab 3: Match PO and Check Approval.

UiPath Python Coded Function project with four deterministic entry points (no LLM calls):

* ``po_lookup``             pure: POST to the ERP PO-lookup URL and apply the business rules. No UiPath SDK.
* ``process_invoice``       one AP_Invoice_Sagar record: read it, run the shared PO lookup, write
                            POMatched / ApprovalNeeded back to it. Idempotent. Lab 10 calls this one.
* ``process_invoice_queue`` standalone wrapper: drain InvoiceQueue_Sagar; each transaction's Reference is a
                            record Id handed to process_invoice; mark it Successful, or Failed (BusinessException).
* ``get_invoice_status``    read-only lifecycle fields of one record for the Lab 10 wait loop. Never writes.

Business rules:
    POMatched      = po.found AND po.vendorActive AND |invoiceTotal - openAmount| <= 2% of openAmount
    ApprovalNeeded = NOT POMatched OR invoiceTotal > 10,000

Configuration (environment):
    ERP_PO_LOOKUP_URL   complete PO-lookup URL, used as is (a hosted value is a signed URL; never logged)
                        default http://localhost:8080/api/po-lookup
    ERP_API_URL         base-URL fallback when ERP_PO_LOOKUP_URL is unset; /api/po-lookup is appended
    ERP_API_TOKEN       optional bearer token sent as Authorization: Bearer
    ERP_TIMEOUT_SECONDS HTTP timeout for the ERP call, default 10

Data Fabric casing: the uip df CLI re-cases acronyms (PoNumber, PoMatched) while the Python SDK returns
schema names (PONumber, POMatched). Reads match case-insensitively; writes use the schema names.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

# At INFO, httpx logs every request URL, including the access_token of a signed ERP URL.
logging.getLogger("httpx").setLevel(logging.WARNING)

import httpx
from pydantic import BaseModel, Field, ValidationError
from uipath.platform import UiPath
from uipath.platform.constants import ENV_ROBOT_KEY
from uipath.tracing import traced

logger = logging.getLogger("POMatch_Sagar")

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

DEFAULT_ERP_API_URL = "http://localhost:8080"
PO_LOOKUP_PATH = "/api/po-lookup"
DEFAULT_ERP_PO_LOOKUP_URL = f"{DEFAULT_ERP_API_URL}{PO_LOOKUP_PATH}"

DEFAULT_ENTITY_NAME = "AP_Invoice_Sagar"
DEFAULT_QUEUE_NAME = "InvoiceQueue_Sagar"
# Full path; the bare folder name returns 400 "Folder does not exist or the user does not have access".
DEFAULT_FOLDER_PATH = "Agentic Bootcamp/APAutomation_Sagar"
DEFAULT_MAX_ITEMS = 50

PO_TOLERANCE = 0.02
APPROVAL_THRESHOLD = 10_000.0

# AP_Invoice_Sagar schema names (exact case). Writes use exactly these.
FIELD_VENDOR_NAME = "VendorName"
FIELD_PO_NUMBER = "PONumber"
FIELD_TOTAL_AMOUNT = "TotalAmount"
FIELD_CURRENCY = "Currency"
FIELD_PO_MATCHED = "POMatched"
FIELD_APPROVAL_NEEDED = "ApprovalNeeded"
FIELD_POSTED_TO_ERP = "PostedToERP"
FIELD_LIFECYCLE_STATE = "InvoiceLifecycleState"
FIELD_REVIEWED_BY = "ReviewedBy"  # added in Lab 5; may not exist yet
FIELD_REVIEWED_AT = "ReviewedAt"  # added in Lab 5; may not exist yet
REQUIRED_FIELDS = (
    FIELD_VENDOR_NAME, FIELD_PO_NUMBER, FIELD_TOTAL_AMOUNT, FIELD_CURRENCY, FIELD_PO_MATCHED, FIELD_APPROVAL_NEEDED,
)

_ACCESS_TOKEN_RE = re.compile(r"(access_token=)[^&#\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Replace every access_token query value with *** before text reaches a log or an output."""
    return _ACCESS_TOKEN_RE.sub(r"\1***", text or "")


def erp_api_url() -> str:
    """Base URL fallback (ERP_API_URL), read at call time."""
    return os.getenv("ERP_API_URL", DEFAULT_ERP_API_URL).rstrip("/")


def erp_po_lookup_url() -> str:
    """The complete PO-lookup URL: ERP_PO_LOOKUP_URL as supplied, else ERP_API_URL + /api/po-lookup."""
    complete = os.getenv("ERP_PO_LOOKUP_URL", "").strip()
    return complete or f"{erp_api_url()}{PO_LOOKUP_PATH}"


def _erp_client() -> httpx.Client:
    """HTTP client for the ERP call. Tests swap it for an httpx.MockTransport client."""
    return httpx.Client(timeout=float(os.getenv("ERP_TIMEOUT_SECONDS", "10")))


_sdk: UiPath | None = None


def sdk() -> UiPath:
    """Lazy SDK singleton; never instantiate UiPath() at import time."""
    global _sdk
    if _sdk is None:
        _sdk = UiPath()
    return _sdk


# --------------------------------------------------------------------------------------
# Shared PO rules
# --------------------------------------------------------------------------------------


class POLookupInput(BaseModel):
    vendor_name: str = ""
    po_number: str = ""
    invoice_total: float = 0.0
    currency: str = "USD"


class POLookupOutput(BaseModel):
    po_matched: bool = False
    approval_required: bool = True  # conservative until the ERP proves otherwise
    open_amount: float = 0.0
    match_reason: str = ""  # MATCHED | PO_NOT_FOUND | VENDOR_INACTIVE | OUTSIDE_TOLERANCE; empty on error
    error_type: str = ""  # INVALID_INPUT | ERP_HTTP_ERROR | ERP_MALFORMED_RESPONSE | ERP_UNREACHABLE; empty on success
    error_message: str = ""


class MalformedErpResponse(ValueError):
    """The ERP answered 200 with a body that does not follow samplepolookup.md."""


def evaluate_po(*, found: bool, vendor_active: bool, open_amount: float, invoice_total: float) -> tuple[bool, bool, str]:
    """Apply the business rules. Returns (po_matched, approval_required, match_reason)."""
    if not found:
        matched, reason = False, "PO_NOT_FOUND"
    elif not vendor_active:
        matched, reason = False, "VENDOR_INACTIVE"
    elif abs(invoice_total - open_amount) > PO_TOLERANCE * open_amount:
        matched, reason = False, "OUTSIDE_TOLERANCE"
    else:
        matched, reason = True, "MATCHED"
    return matched, (not matched) or invoice_total > APPROVAL_THRESHOLD, reason


def parse_po_response(payload: Any) -> dict[str, Any]:
    """Strictly validate {"po": {found, vendorActive, openAmount, currency}}; never guess from a partial answer."""
    if not isinstance(payload, dict) or not isinstance(payload.get("po"), dict):
        raise MalformedErpResponse("response has no 'po' object")
    po = payload["po"]
    found, vendor_active, open_amount = po.get("found"), po.get("vendorActive"), po.get("openAmount")
    if not isinstance(found, bool):
        raise MalformedErpResponse("po.found is missing or not a boolean")
    if not isinstance(vendor_active, bool):
        raise MalformedErpResponse("po.vendorActive is missing or not a boolean")
    if isinstance(open_amount, bool) or not isinstance(open_amount, (int, float)):
        raise MalformedErpResponse("po.openAmount is missing or not a number")
    return {
        "found": found,
        "vendor_active": vendor_active,
        "open_amount": float(open_amount),
        "currency": str(po.get("currency") or ""),
    }


def _po_lookup(input: POLookupInput) -> POLookupOutput:
    """Shared PO lookup used by every entry point. Returns errors, never raises; on error it fails safe
    (po_matched False, approval_required True) and the message never contains the access_token."""
    out = POLookupOutput()
    if not input.po_number.strip():
        out.error_type, out.error_message = "INVALID_INPUT", "po_number is required"
        return out

    url = erp_po_lookup_url()
    shown = redact(url)
    body = {
        "vendorName": input.vendor_name,
        "poNumber": input.po_number,
        "invoiceTotal": input.invoice_total,
        "currency": input.currency,
    }
    token = os.getenv("ERP_API_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else None

    try:
        with _erp_client() as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        out.error_type = "ERP_UNREACHABLE"
        out.error_message = redact(f"POST {shown} failed: {type(exc).__name__}: {exc}")
        return out

    if response.status_code != 200:
        out.error_type = "ERP_HTTP_ERROR"
        out.error_message = redact(f"POST {shown} returned HTTP {response.status_code}: {response.text[:200]}")
        return out

    try:
        po = parse_po_response(response.json())
    except ValueError as exc:  # non-JSON body or MalformedErpResponse
        out.error_type = "ERP_MALFORMED_RESPONSE"
        out.error_message = redact(f"POST {shown} returned a malformed response: {exc}")
        return out

    out.po_matched, out.approval_required, out.match_reason = evaluate_po(
        found=po["found"], vendor_active=po["vendor_active"], open_amount=po["open_amount"],
        invoice_total=input.invoice_total,
    )
    out.open_amount = po["open_amount"]
    return out


# --------------------------------------------------------------------------------------
# Shared Data Fabric helpers
# --------------------------------------------------------------------------------------


class BusinessError(Exception):
    def __init__(self, message: str, error_type: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def _get_field(data: dict[str, Any], name: str, default: Any = None) -> Any:
    """Read a field by schema name; exact match first, then case-insensitive (PoNumber, PoMatched, ...)."""
    if name in data:
        return data[name]
    wanted = name.lower()
    for key, value in data.items():
        if isinstance(key, str) and key.lower() == wanted:
            return value
    return default


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    return default


def _to_float(value: Any, field_name: str) -> float:
    if value is None or value == "":
        raise BusinessError(f"record field {field_name} is empty", "INVALID_RECORD")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise BusinessError(f"record field {field_name} is not numeric", "INVALID_RECORD") from exc


def _resolve_entity(entity_name: str, required_fields: tuple[str, ...] = REQUIRED_FIELDS) -> str:
    """Entity Id by name (Data Fabric is tenant-scoped; no folder). Verifies exact schema names when returned."""
    try:
        entity = sdk().entities.retrieve_by_name(entity_name)
    except Exception as exc:
        raise BusinessError(f"entity {entity_name} could not be resolved: {exc}", "ENTITY_RESOLUTION_FAILED") from exc
    names = {f.name for f in (entity.fields or [])}
    missing = [n for n in required_fields if names and n not in names]
    if missing:
        raise BusinessError(f"entity {entity_name} is missing fields {missing}", "ENTITY_RESOLUTION_FAILED")
    return entity.id


def _read_record(entity_id: str, record_id: str) -> dict[str, Any]:
    try:
        record = sdk().entities.get_record(entity_id, record_id)
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status == 404 or "404" in str(exc) or "not found" in str(exc).lower():
            raise BusinessError(f"record {record_id} could not be read: not found", "RECORD_NOT_FOUND") from exc
        raise BusinessError(f"record {record_id} could not be read: {exc}", "RECORD_READ_FAILED") from exc
    return record.model_dump(by_alias=True)


def _write_po_result(entity_id: str, record_id: str, po_matched: bool, approval_needed: bool) -> None:
    try:
        sdk().entities.update_record(
            entity_id, record_id, {FIELD_PO_MATCHED: po_matched, FIELD_APPROVAL_NEEDED: approval_needed}
        )
    except Exception as exc:
        raise BusinessError(f"record {record_id} could not be updated: {exc}", "RECORD_UPDATE_FAILED") from exc


# --------------------------------------------------------------------------------------
# 1. po_lookup
# --------------------------------------------------------------------------------------


@traced(name="po_lookup", run_type="uipath")
def po_lookup(input: POLookupInput) -> POLookupOutput:
    """Look one invoice up against its PO in the ERP and apply the rules. No UiPath SDK calls."""
    try:
        return _po_lookup(input)
    except Exception as exc:  # contract: return, never raise
        return POLookupOutput(error_type="ERP_UNREACHABLE", error_message=redact(f"{type(exc).__name__}: {exc}"))


# --------------------------------------------------------------------------------------
# 2. process_invoice
# --------------------------------------------------------------------------------------


class ProcessInvoiceInput(BaseModel):
    record_id: str = ""
    entity_name: str = DEFAULT_ENTITY_NAME


class ProcessInvoiceOutput(BaseModel):
    record_id: str = ""
    po_matched: bool = False
    approval_required: bool = True
    open_amount: float = 0.0
    match_reason: str = ""
    error_type: str = ""
    error_message: str = ""


def _process_invoice(input: ProcessInvoiceInput, entity_id: str | None = None) -> ProcessInvoiceOutput:
    """Shared per-record implementation. The queue wrapper passes a pre-resolved entity_id."""
    record_id = input.record_id.strip()
    out = ProcessInvoiceOutput(record_id=record_id)
    try:
        if not record_id:
            raise BusinessError("record_id is required", "INVALID_INPUT")
        entity_id = entity_id or _resolve_entity(input.entity_name)
        data = _read_record(entity_id, record_id)

        lookup = _po_lookup(
            POLookupInput(
                vendor_name=_to_text(_get_field(data, FIELD_VENDOR_NAME)),
                po_number=_to_text(_get_field(data, FIELD_PO_NUMBER)),
                invoice_total=_to_float(_get_field(data, FIELD_TOTAL_AMOUNT), FIELD_TOTAL_AMOUNT),
                currency=_to_text(_get_field(data, FIELD_CURRENCY)) or "USD",
            )
        )
        if lookup.error_type:
            # No write: a failed lookup is "no answer", never a guessed match.
            raise BusinessError(f"PO lookup failed: {lookup.error_message}", lookup.error_type)

        unchanged = (
            _get_field(data, FIELD_PO_MATCHED) is lookup.po_matched
            and _get_field(data, FIELD_APPROVAL_NEEDED) is lookup.approval_required
        )
        if not unchanged:
            _write_po_result(entity_id, record_id, lookup.po_matched, lookup.approval_required)

        out.po_matched = lookup.po_matched
        out.approval_required = lookup.approval_required
        out.open_amount = lookup.open_amount
        out.match_reason = lookup.match_reason
        # Log only the record Id and the outcome; never vendor, tax id or amounts.
        logger.info(
            "record %s: POMatched=%s ApprovalNeeded=%s (%s)%s",
            record_id, lookup.po_matched, lookup.approval_required, lookup.match_reason,
            " unchanged" if unchanged else "",
        )
    except BusinessError as exc:
        out.error_type, out.error_message = exc.error_type, redact(str(exc))
    except Exception as exc:
        out.error_type, out.error_message = "UNEXPECTED_ERROR", redact(f"{type(exc).__name__}: {exc}")
    return out


@traced(name="process_invoice", run_type="uipath")
def process_invoice(input: ProcessInvoiceInput) -> ProcessInvoiceOutput:
    """Match one AP_Invoice record against its PO and write POMatched / ApprovalNeeded on it."""
    return _process_invoice(input)


# --------------------------------------------------------------------------------------
# 3. process_invoice_queue
# --------------------------------------------------------------------------------------


class ProcessQueueInput(BaseModel):
    queue_name: str = DEFAULT_QUEUE_NAME
    folder_path: str = DEFAULT_FOLDER_PATH
    entity_name: str = DEFAULT_ENTITY_NAME
    max_items: int = DEFAULT_MAX_ITEMS


class ProcessQueueOutput(BaseModel):
    processed: int = 0
    matched: int = 0
    approval_required: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)  # one line per failed transaction
    error_type: str = ""  # set only when the run itself could not proceed
    error_message: str = ""


def _is_empty_body_error(exc: BaseException) -> bool:
    """The SDK returns response.json(); an empty 200/204 body raises a decode error although the call succeeded."""
    if isinstance(exc, json.JSONDecodeError):
        return True
    return type(exc) is ValueError and "Expecting value" in str(exc)


def _next_transaction(queue_name: str, folder_path: str) -> dict[str, Any] | None:
    """Start the next transaction; None when the queue has no New items (204, empty body)."""
    try:
        item = sdk().queues.create_transaction_item(
            {}, queue_name=queue_name, no_robot=not os.getenv(ENV_ROBOT_KEY), folder_path=folder_path
        )
    except ValueError as exc:
        if isinstance(exc, ValidationError) or not _is_empty_body_error(exc):
            raise
        return None
    if not isinstance(item, dict) or not item.get("Key"):
        return None
    return item


def _complete(transaction_id: int, result: dict[str, Any], input: ProcessQueueInput) -> None:
    """SetTransactionResult by the numeric Id. An empty 200 body is success."""
    try:
        sdk().queues.complete_transaction_item(
            str(transaction_id), result, queue_name=input.queue_name, folder_path=input.folder_path
        )
    except ValueError as exc:
        if isinstance(exc, ValidationError) or not _is_empty_body_error(exc):
            raise


def _transaction_id(transaction: dict[str, Any]) -> int | None:
    value = transaction.get("Id")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


@traced(name="process_invoice_queue", run_type="uipath")
def process_invoice_queue(input: ProcessQueueInput) -> ProcessQueueOutput:
    """Drain the invoice queue; every transaction's Reference is a record Id delegated to process_invoice."""
    out = ProcessQueueOutput()
    try:
        entity_id = _resolve_entity(input.entity_name)
    except BusinessError as exc:
        out.error_type, out.error_message = exc.error_type, redact(str(exc))
        return out

    while out.processed < input.max_items:
        try:
            transaction = _next_transaction(input.queue_name, input.folder_path)
        except Exception as exc:  # queue missing, wrong folder, auth: the run cannot continue
            out.error_type = "QUEUE_ERROR"
            out.error_message = redact(f"could not start a transaction on {input.queue_name} in {input.folder_path}: {exc}")
            break
        if transaction is None:
            break

        out.processed += 1
        transaction_id = _transaction_id(transaction)
        record_id = _to_text(transaction.get("Reference")).strip()
        reference = record_id or "<no reference>"
        if transaction_id is None:
            out.failed += 1
            out.errors.append(f"record {reference}: transaction has no numeric Id and could not be completed")
            continue

        if record_id:
            result = _process_invoice(
                ProcessInvoiceInput(record_id=record_id, entity_name=input.entity_name), entity_id=entity_id
            )
        else:
            result = ProcessInvoiceOutput(error_type="INVALID_INPUT", error_message="transaction has no Reference")

        if result.error_type:
            out.failed += 1
            message = redact(f"record {reference}: {result.error_type}: {result.error_message}")
            out.errors.append(message)
            outcome = {"IsSuccessful": False, "ProcessingException": {"Type": "BusinessException", "Reason": message[:1000]}}
        else:
            out.matched += int(result.po_matched)
            out.approval_required += int(result.approval_required)
            outcome = {
                "IsSuccessful": True,
                "Output": {
                    FIELD_PO_MATCHED: result.po_matched,
                    FIELD_APPROVAL_NEEDED: result.approval_required,
                    "MatchReason": result.match_reason,
                },
            }
        try:
            _complete(transaction_id, outcome, input)
        except Exception as exc:
            if result.error_type:
                out.errors.append(redact(f"record {reference}: could not mark the transaction Failed: {exc}"))
            else:  # the record is already updated; say so, so the queue can be reconciled
                out.errors.append(redact(f"record {reference}: updated, but the transaction could not be marked Successful: {exc}"))
    return out


# --------------------------------------------------------------------------------------
# 4. get_invoice_status
# --------------------------------------------------------------------------------------


class InvoiceStatusInput(BaseModel):
    record_id: str = ""
    entity_name: str = DEFAULT_ENTITY_NAME


class InvoiceStatusOutput(BaseModel):
    record_id: str = ""
    invoice_lifecycle_state: str = ""
    approval_needed: bool = True  # unset -> True
    posted_to_erp: bool = False  # unset -> False
    reviewed_by: str = ""
    reviewed_at: str = ""
    found: bool = False
    error_type: str = ""
    error_message: str = ""


@traced(name="get_invoice_status", run_type="uipath")
def get_invoice_status(input: InvoiceStatusInput) -> InvoiceStatusOutput:
    """Read one record's lifecycle fields. Performs no write of any kind."""
    record_id = input.record_id.strip()
    out = InvoiceStatusOutput(record_id=record_id)
    try:
        if not record_id:
            raise BusinessError("record_id is required", "INVALID_INPUT")
        # No required fields: the review fields arrive in later labs.
        data = _read_record(_resolve_entity(input.entity_name, required_fields=()), record_id)
        out.found = True
        out.invoice_lifecycle_state = _to_text(_get_field(data, FIELD_LIFECYCLE_STATE))
        out.approval_needed = _to_bool(_get_field(data, FIELD_APPROVAL_NEEDED), default=True)
        out.posted_to_erp = _to_bool(_get_field(data, FIELD_POSTED_TO_ERP), default=False)
        out.reviewed_by = _to_text(_get_field(data, FIELD_REVIEWED_BY))
        out.reviewed_at = _to_text(_get_field(data, FIELD_REVIEWED_AT))
    except BusinessError as exc:
        out.error_type, out.error_message = exc.error_type, redact(str(exc))
    except Exception as exc:
        out.error_type, out.error_message = "UNEXPECTED_ERROR", redact(f"{type(exc).__name__}: {exc}")
    return out
