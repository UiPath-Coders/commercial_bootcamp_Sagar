"""POMatch_Reference — Lab 3 reference solution: Match PO & Check Approval.

UiPath Python Coded Function project (built with the uipath-functions skill) for the
Commercial Bootcamp Invoice-to-Pay process. Four deterministic entry points, no LLM calls:

* ``po_lookup``             — pure. POST to the mock ERP PO-lookup URL and apply the business
                              rules. No UiPath SDK calls, so it runs and tests offline.
* ``process_invoice``       — one Data Fabric record. Read ``AP_Invoice_<user_name>`` record
                              ``record_id``, run the shared po_lookup implementation, write
                              ``POMatched`` / ``ApprovalNeeded`` back to that same record. Safe to
                              re-run. This is the per-record contract Lab 10's Maestro process calls.
* ``process_invoice_queue`` — standalone Lab 3 wrapper. Drain ``InvoiceQueue_<user_name>``; every
                              transaction's Reference is a record Id that is handed to
                              ``process_invoice``; the transaction is marked Successful, or Failed
                              with a BusinessException, and the loop continues.
* ``get_invoice_status``    — read-only. Returns the lifecycle fields of one record so a Maestro
                              wait loop can observe the Lab 6 reviewer decision. Never writes.

Business rules (docs/commercial-process.md):
    POMatched      = po.found AND po.vendorActive AND |invoiceTotal - openAmount| <= 2% * openAmount
    ApprovalNeeded = NOT POMatched OR invoiceTotal > 10,000

Naming: this reference uses the suffix ``Reference`` wherever a participant would have their
first name (``POMatch_Reference``, ``InvoiceQueue_Reference``, ``APAutomation_Reference``,
``AP_Invoice_Reference``). Set ``BOOTCAMP_USER_NAME`` (or the individual variables below) to
rename without touching the code.

Configuration:
    ERP_PO_LOOKUP_URL       COMPLETE PO-lookup URL, used as is  default http://localhost:8080/api/po-lookup
                            (a hosted value is a signed URL with ?access_token=...; never logged)
    ERP_API_URL             legacy base URL, used only when ERP_PO_LOOKUP_URL is unset;
                            ``/api/po-lookup`` is appended to it
    ERP_API_TOKEN           local-only bearer token override  default empty
    ERP_API_TOKEN_ASSET     Orchestrator asset holding a bearer token (hosted mode) default empty
    ERP_TIMEOUT_SECONDS     HTTP timeout for the ERP call     default 10
    BOOTCAMP_USER_NAME      <user_name> suffix                default Reference
    INVOICE_QUEUE_NAME      queue to drain                    default InvoiceQueue_<user_name>
    AP_FOLDER_PATH          Orchestrator folder of the queue  default Agentic Bootcamp/APAutomation_<user_name>
                            (the FULL path; the bare folder name returns 400 Folder does not exist)
    AP_INVOICE_ENTITY_NAME  Data Fabric entity (tenant scope) default AP_Invoice_<user_name>
    AP_INVOICE_ENTITY_ID    optional entity Id; skips the lookup by name when set

Data Fabric casing: the uip df CLI prints acronym fields re-cased (``PoNumber``, ``PoMatched``,
``GlAccount``) and omits null fields, while the Python SDK returns the schema system names
(``PONumber``, ``POMatched``, ``PostedToERP``). Reads are therefore case-insensitive
(``_get_field``); writes always use the schema system names.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError
from uipath.platform import UiPath
from uipath.platform.constants import ENV_ROBOT_KEY  # "UIPATH_ROBOT_KEY", set by the robot on a job
from uipath.tracing import traced

logger = logging.getLogger("POMatch_Reference")
# At INFO, httpx logs every request URL. A hosted ERP URL is signed (?access_token=...), so keep httpx at
# WARNING or the token lands in the console and in the job logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

USER_NAME = os.getenv("BOOTCAMP_USER_NAME", "Reference")  # the <user_name> placeholder

DEFAULT_ERP_API_URL = "http://localhost:8080"
PO_LOOKUP_PATH = "/api/po-lookup"
DEFAULT_ERP_PO_LOOKUP_URL = f"{DEFAULT_ERP_API_URL}{PO_LOOKUP_PATH}"
DEFAULT_QUEUE_NAME = os.getenv("INVOICE_QUEUE_NAME", f"InvoiceQueue_{USER_NAME}")
# Full folder path. The reference resolves to "Agentic Bootcamp/APAutomation_Reference"; participants use
# "Agentic Bootcamp/APAutomation_<user_name>". The bare name "APAutomation_<user_name>" returns
# 400 "Folder does not exist or the user does not have access".
DEFAULT_FOLDER_PATH = os.getenv("AP_FOLDER_PATH", f"Agentic Bootcamp/APAutomation_{USER_NAME}")
DEFAULT_ENTITY_NAME = os.getenv("AP_INVOICE_ENTITY_NAME", f"AP_Invoice_{USER_NAME}")
DEFAULT_ENTITY_ID = os.getenv("AP_INVOICE_ENTITY_ID", "")
DEFAULT_TOKEN_ASSET_NAME = os.getenv("ERP_API_TOKEN_ASSET", "")
DEFAULT_MAX_ITEMS = 50

PO_TOLERANCE = 0.02  # 2% of the PO open amount
APPROVAL_THRESHOLD = 10_000.0  # same numeric threshold regardless of currency (stated as USD)

# AP_Invoice_<user_name> schema system names (PascalCase, no spaces). Writes use exactly these;
# reads match them case-insensitively (see _get_field).
FIELD_VENDOR_NAME = "VendorName"
FIELD_PO_NUMBER = "PONumber"
FIELD_TOTAL_AMOUNT = "TotalAmount"
FIELD_CURRENCY = "Currency"
FIELD_PO_MATCHED = "POMatched"
FIELD_APPROVAL_NEEDED = "ApprovalNeeded"
FIELD_POSTED_TO_ERP = "PostedToERP"
FIELD_LIFECYCLE_STATE = "InvoiceLifecycleState"  # added for Lab 6 / Lab 10; may not exist yet
FIELD_REVIEWED_BY = "ReviewedBy"  # added by Lab 6; Day 1 entities do not have it
FIELD_REVIEWED_AT = "ReviewedAt"  # added by Lab 6; Day 1 entities do not have it
READ_FIELDS = (FIELD_VENDOR_NAME, FIELD_PO_NUMBER, FIELD_TOTAL_AMOUNT, FIELD_CURRENCY)
WRITE_FIELDS = (FIELD_PO_MATCHED, FIELD_APPROVAL_NEEDED)

_ACCESS_TOKEN_RE = re.compile(r"(access_token=)[^&#\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Hide any ``access_token`` query value (signed hosted ERP URL) before it reaches a log or output."""
    return _ACCESS_TOKEN_RE.sub(r"\1***", text or "")


def erp_api_url() -> str:
    """Legacy base URL of the mock ERP (``ERP_API_URL``), read at call time."""
    return os.getenv("ERP_API_URL", DEFAULT_ERP_API_URL).rstrip("/")


def erp_po_lookup_url() -> str:
    """The complete PO-lookup URL.

    ``ERP_PO_LOOKUP_URL`` wins and is used exactly as supplied (a hosted value is a signed URL whose
    query carries ``access_token``; nothing is appended to it). When it is unset, the legacy
    ``ERP_API_URL`` base URL plus ``/api/po-lookup`` is used, defaulting to the local mock ERP.
    """
    complete = os.getenv("ERP_PO_LOOKUP_URL", "").strip()
    if complete:
        return complete
    return f"{erp_api_url()}{PO_LOOKUP_PATH}"


def erp_timeout_seconds() -> float:
    return float(os.getenv("ERP_TIMEOUT_SECONDS", "10"))


def _erp_client() -> httpx.Client:
    """HTTP client used for the ERP call. Tests swap this for an httpx.MockTransport."""
    return httpx.Client(timeout=erp_timeout_seconds())


# Lazy SDK singleton — never instantiate UiPath() at module level.
_sdk: UiPath | None = None


def sdk() -> UiPath:
    global _sdk
    if _sdk is None:
        _sdk = UiPath()
    return _sdk


# --------------------------------------------------------------------------------------
# Function 1 — po_lookup (pure: HTTP to the ERP + business rules, no UiPath SDK)
# --------------------------------------------------------------------------------------


class POLookupInput(BaseModel):
    vendor_name: str = ""
    po_number: str = ""
    invoice_total: float = 0.0
    currency: str = "USD"


class POLookupOutput(BaseModel):
    po_matched: bool = False
    approval_required: bool = True  # conservative until the lookup proves otherwise
    open_amount: float = 0.0
    match_reason: str = ""  # MATCHED | PO_NOT_FOUND | VENDOR_INACTIVE | OUTSIDE_TOLERANCE | "" on error
    error_type: str = ""  # empty on success
    error_message: str = ""  # empty on success


class MalformedErpResponse(ValueError):
    """The ERP answered 200 but the body does not follow samplepolookup.md."""


def evaluate_po(*, found: bool, vendor_active: bool, open_amount: float, invoice_total: float) -> tuple[bool, bool, str]:
    """Apply the Lab 3 business rules. Returns (po_matched, approval_required, match_reason)."""
    if not found:
        matched, reason = False, "PO_NOT_FOUND"
    elif not vendor_active:
        matched, reason = False, "VENDOR_INACTIVE"
    elif abs(invoice_total - open_amount) > PO_TOLERANCE * open_amount:
        matched, reason = False, "OUTSIDE_TOLERANCE"
    else:
        matched, reason = True, "MATCHED"
    approval_required = (not matched) or invoice_total > APPROVAL_THRESHOLD
    return matched, approval_required, reason


def parse_po_response(payload: Any) -> dict[str, Any]:
    """Validate the ``{"po": {found, vendorActive, openAmount, currency}}`` shape strictly.

    Anything that is not exactly a boolean/boolean/number is rejected — the function must never
    guess a match from a partial or mistyped answer.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("po"), dict):
        raise MalformedErpResponse("response has no 'po' object")
    po = payload["po"]
    found = po.get("found")
    vendor_active = po.get("vendorActive")
    open_amount = po.get("openAmount")
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


def _po_lookup(input: POLookupInput, api_token: str = "") -> POLookupOutput:
    """Look one invoice up against its PO in the mock ERP and apply the business rules.

    Shared by every entry point. Errors are returned, never raised: ``error_type`` is one of
    INVALID_INPUT, ERP_UNREACHABLE, ERP_HTTP_ERROR, ERP_MALFORMED_RESPONSE. On any error
    ``po_matched`` is False and ``approval_required`` is True (fail safe: route to a human), and
    callers must treat a non-empty ``error_type`` as "no answer", not as a business result.
    Error messages never contain the ``access_token`` of a signed URL.
    """
    out = POLookupOutput()

    if not input.po_number.strip():
        out.error_type = "INVALID_INPUT"
        out.error_message = "po_number is required"
        return out

    url = erp_po_lookup_url()
    shown = redact(url)  # the only form of the URL that may appear in a message
    body = {
        "vendorName": input.vendor_name,
        "poNumber": input.po_number,
        "invoiceTotal": input.invoice_total,
        "currency": input.currency,
    }

    try:
        with _erp_client() as client:
            headers = {"Authorization": f"Bearer {api_token}"} if api_token else None
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:  # connection refused, DNS, timeout, invalid URL, ...
        out.error_type = "ERP_UNREACHABLE"
        out.error_message = redact(f"POST {shown} failed: {type(exc).__name__}: {exc}")
        return out

    if response.status_code != 200:
        out.error_type = "ERP_HTTP_ERROR"
        out.error_message = redact(f"POST {shown} returned HTTP {response.status_code}: {response.text[:200]}")
        return out

    try:
        payload = response.json()
    except ValueError as exc:
        out.error_type = "ERP_MALFORMED_RESPONSE"
        out.error_message = f"POST {shown} returned a non-JSON body: {exc}"
        return out

    try:
        po = parse_po_response(payload)
    except MalformedErpResponse as exc:
        out.error_type = "ERP_MALFORMED_RESPONSE"
        out.error_message = f"POST {shown}: {exc}"
        return out

    out.po_matched, out.approval_required, out.match_reason = evaluate_po(
        found=po["found"],
        vendor_active=po["vendor_active"],
        open_amount=po["open_amount"],
        invoice_total=input.invoice_total,
    )
    out.open_amount = po["open_amount"]
    return out


@traced(name="po_lookup", run_type="uipath")
def po_lookup(input: POLookupInput) -> POLookupOutput:
    """Public function entry point; local callers may supply ERP_API_TOKEN through the environment."""
    return _po_lookup(input, os.getenv("ERP_API_TOKEN", ""))


# --------------------------------------------------------------------------------------
# Shared Data Fabric / configuration helpers (used by the three SDK entry points)
# --------------------------------------------------------------------------------------


class BusinessError(Exception):
    """A per-record problem. ``error_type`` names it in the function output."""

    def __init__(self, message: str, error_type: str = "INVALID_RECORD") -> None:
        super().__init__(message)
        self.error_type = error_type


class RecordNotFound(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "RECORD_NOT_FOUND")


def _get_field(data: dict[str, Any], name: str, default: Any = None) -> Any:
    """Read a record field by its schema system name, tolerating the API's casing.

    Data Fabric returns ``PoNumber`` / ``PoMatched`` / ``PostedToErp`` for schema names ``PONumber`` /
    ``POMatched`` / ``PostedToERP``. An exact match wins; otherwise the first case-insensitive match.
    """
    if name in data:
        return data[name]
    wanted = name.lower()
    for key, value in data.items():
        if isinstance(key, str) and key.lower() == wanted:
            return value
    return default


def _to_float(value: Any, field_name: str) -> float:
    if value is None or value == "":
        raise BusinessError(f"record field {field_name} is empty")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise BusinessError(f"record field {field_name} is not numeric: {value!r}") from exc


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return default


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def _entity_id_for(entity_name: str) -> str:
    """AP_INVOICE_ENTITY_ID applies only to the default entity name."""
    return DEFAULT_ENTITY_ID if entity_name == DEFAULT_ENTITY_NAME else ""


def _resolve_entity(entity_name: str, entity_id: str = "", required_fields: tuple[str, ...] = READ_FIELDS + WRITE_FIELDS) -> str:
    """Return the entity Id and verify the exact, case-sensitive schema system names we depend on."""
    entity = sdk().entities.retrieve(entity_id) if entity_id else sdk().entities.retrieve_by_name(entity_name)
    schema_names = {f.name for f in (entity.fields or [])}
    if schema_names and required_fields:  # some tenants return the schema; when they do, refuse to guess names
        missing = [name for name in required_fields if name not in schema_names]
        if missing:
            raise RuntimeError(
                f"entity {entity.name} ({entity.id}) is missing fields {missing}; "
                "use the exact system names from `uip df entities list --native-only`"
            )
    logger.info("Using entity %s (%s)", entity.name, entity.id)
    return entity.id


def _read_record(entity_id: str, record_id: str) -> dict[str, Any]:
    """Read exactly one record. Raises RecordNotFound (404) or BusinessError (anything else)."""
    try:
        record = sdk().entities.get_record(entity_id, record_id)
    except Exception as exc:  # 404, permissions, ...
        status = getattr(exc, "status_code", None)
        if status == 404 or (status is None and ("404" in str(exc) or "not found" in str(exc).lower())):
            raise RecordNotFound(f"record could not be read: {exc}") from exc
        raise BusinessError(f"record could not be read: {exc}", "RECORD_READ_FAILED") from exc
    return record.model_dump(by_alias=True)


def _erp_api_token(asset_name: str, folder_path: str) -> str:
    """Resolve the hosted-service bearer token without putting its value in traced function input."""
    local_override = os.getenv("ERP_API_TOKEN", "").strip()
    if local_override:
        return local_override
    if not asset_name.strip():
        return ""
    asset = sdk().assets.retrieve(asset_name, folder_path=folder_path)
    for attribute in ("secret_value", "string_value", "value", "credential_password"):
        value = getattr(asset, attribute, None)
        if value:
            return str(value).strip()
    raise RuntimeError(f"asset {asset_name} contains no usable token value")


# --------------------------------------------------------------------------------------
# Function 2 — process_invoice (one record: read -> po_lookup -> write POMatched/ApprovalNeeded)
# --------------------------------------------------------------------------------------


class ProcessInvoiceInput(BaseModel):
    record_id: str = ""
    entity_name: str = DEFAULT_ENTITY_NAME


class ProcessInvoiceOutput(BaseModel):
    record_id: str = ""
    po_matched: bool = False
    approval_required: bool = True  # conservative until the lookup proves otherwise
    open_amount: float = 0.0
    match_reason: str = ""
    error_type: str = ""  # empty on success
    error_message: str = ""


def _process_invoice(
    input: ProcessInvoiceInput, *, entity_id: str | None = None, api_token: str | None = None
) -> ProcessInvoiceOutput:
    """Shared implementation behind ``process_invoice`` (and every queue transaction).

    ``entity_id`` / ``api_token`` let the queue wrapper resolve them once per run; a direct call
    resolves them itself. Never raises. Idempotent: the result depends only on the record's
    VendorName/PONumber/TotalAmount/Currency and the ERP answer, and the write is skipped when the
    record already holds the computed values.
    """
    record_id = input.record_id.strip()
    out = ProcessInvoiceOutput(record_id=record_id)
    try:
        if not record_id:
            raise BusinessError("record_id is required", "INVALID_INPUT")

        if api_token is None:
            try:
                api_token = _erp_api_token(DEFAULT_TOKEN_ASSET_NAME, DEFAULT_FOLDER_PATH)
            except Exception as exc:
                raise BusinessError(f"could not read hosted ERP token asset: {exc}", "ERP_AUTH_CONFIGURATION_FAILED") from exc

        if entity_id is None:
            try:
                entity_id = _resolve_entity(input.entity_name, _entity_id_for(input.entity_name))
            except Exception as exc:
                raise BusinessError(str(exc), "ENTITY_RESOLUTION_FAILED") from exc

        data = _read_record(entity_id, record_id)

        lookup = _po_lookup(
            POLookupInput(
                vendor_name=_to_text(_get_field(data, FIELD_VENDOR_NAME)),
                po_number=_to_text(_get_field(data, FIELD_PO_NUMBER)),
                invoice_total=_to_float(_get_field(data, FIELD_TOTAL_AMOUNT), FIELD_TOTAL_AMOUNT),
                currency=_to_text(_get_field(data, FIELD_CURRENCY)) or "USD",
            ),
            api_token,
        )
        if lookup.error_type:
            # Nothing is written: a failed lookup is "no answer", never a guessed match.
            raise BusinessError(f"PO lookup failed ({lookup.error_type}): {lookup.error_message}", lookup.error_type)

        already = (
            _get_field(data, FIELD_PO_MATCHED) is lookup.po_matched
            and _get_field(data, FIELD_APPROVAL_NEEDED) is lookup.approval_required
        )
        if not already:
            try:
                sdk().entities.update_record(
                    entity_id,
                    record_id,
                    {FIELD_PO_MATCHED: lookup.po_matched, FIELD_APPROVAL_NEEDED: lookup.approval_required},
                )
            except Exception as exc:
                raise BusinessError(f"record could not be updated: {exc}", "RECORD_UPDATE_FAILED") from exc

        out.po_matched = lookup.po_matched
        out.approval_required = lookup.approval_required
        out.open_amount = lookup.open_amount
        out.match_reason = lookup.match_reason
        # Only the record Id and the outcome are logged — never vendor, tax id, bank or amounts.
        logger.info(
            "record %s -> POMatched=%s ApprovalNeeded=%s (%s)%s",
            record_id, lookup.po_matched, lookup.approval_required, lookup.match_reason,
            " unchanged" if already else "",
        )
    except BusinessError as exc:
        out.error_type = exc.error_type
        out.error_message = redact(str(exc))
    except Exception as exc:  # the Coded Function contract: return, never raise
        out.error_type = "UNEXPECTED_ERROR"
        out.error_message = redact(f"{type(exc).__name__}: {exc}")
    return out


@traced(name="process_invoice", run_type="uipath")
def process_invoice(input: ProcessInvoiceInput) -> ProcessInvoiceOutput:
    """Match one AP_Invoice record against its PO and stamp POMatched / ApprovalNeeded on it."""
    return _process_invoice(input)


# --------------------------------------------------------------------------------------
# Function 3 — process_invoice_queue (queue wrapper; every transaction -> process_invoice)
# --------------------------------------------------------------------------------------


class ProcessQueueInput(BaseModel):
    queue_name: str = DEFAULT_QUEUE_NAME
    folder_path: str = DEFAULT_FOLDER_PATH
    entity_name: str = DEFAULT_ENTITY_NAME
    entity_id: str = DEFAULT_ENTITY_ID  # optional: when set, the entity is not looked up by name
    erp_api_token_asset_name: str = DEFAULT_TOKEN_ASSET_NAME  # hosted mode; token value is never an input
    max_items: int = DEFAULT_MAX_ITEMS


class ProcessQueueOutput(BaseModel):
    processed: int = 0  # transactions taken from the queue (successful + failed)
    matched: int = 0  # successful transactions with POMatched = true
    approval_required: int = 0  # successful transactions with ApprovalNeeded = true
    failed: int = 0  # transactions marked Failed (BusinessException)
    errors: list[str] = Field(default_factory=list)  # one line per failed transaction
    error_type: str = ""  # set only when the run itself could not proceed
    error_message: str = ""


def _next_transaction(queue_name: str, folder_path: str) -> dict[str, Any] | None:
    """Start the next transaction (Orchestrator StartTransaction). None when the queue has no New items.

    The SDK returns ``response.json()``; an empty queue is a 204 with no body, so the JSON decode
    raises ``json.JSONDecodeError``. That is the normal end-of-queue signal, not an error.

    The transaction is associated with the robot only when running as a job: the SDK reads the
    robot key from ``UIPATH_ROBOT_KEY`` and raises ``ValueError`` when it is missing, so a local run
    (``uip function run``) passes ``no_robot=True`` instead.
    """
    no_robot = not os.getenv(ENV_ROBOT_KEY)
    try:
        item = sdk().queues.create_transaction_item(
            {}, queue_name=queue_name, no_robot=no_robot, folder_path=folder_path
        )
    except json.JSONDecodeError:
        return None
    if not isinstance(item, dict) or not item.get("Key"):
        return None
    return item


def _is_empty_body_error(exc: BaseException) -> bool:
    """True for the decode error ``response.json()`` raises on an empty 200 body.

    Only a JSON decode error qualifies; a pydantic ValidationError (also a ValueError) or any HTTP
    error is a real failure.
    """
    if isinstance(exc, json.JSONDecodeError):
        return True
    return type(exc) is ValueError and "Expecting value" in str(exc)


def _complete(transaction_id: int | str, result: dict[str, Any], input: ProcessQueueInput) -> None:
    """Set the transaction result (Orchestrator ``Queues({Id})/SetTransactionResult``).

    Keyed by the NUMERIC transaction ``Id`` — the GUID ``Key`` returns 404 and leaves the item
    InProgress. Orchestrator answers 200 with an empty body, which makes the SDK's
    ``response.json()`` raise ``Expecting value: line 1 column 1``; the result was stored, so that is
    success. HTTP 4xx/5xx errors are raised by the SDK before the decode and still propagate.
    """
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
    """Drain InvoiceQueue_<user_name>; every transaction's Reference is handed to process_invoice."""
    out = ProcessQueueOutput()

    try:
        api_token = _erp_api_token(input.erp_api_token_asset_name, input.folder_path)
    except Exception as exc:
        out.error_type = "ERP_AUTH_CONFIGURATION_FAILED"
        out.error_message = redact(f"could not read hosted ERP token asset {input.erp_api_token_asset_name}: {exc}")
        return out

    try:
        entity_id = _resolve_entity(input.entity_name, input.entity_id)
    except Exception as exc:
        out.error_type = "ENTITY_RESOLUTION_FAILED"
        out.error_message = redact(str(exc))
        return out

    while out.processed < input.max_items:
        try:
            transaction = _next_transaction(input.queue_name, input.folder_path)
        except Exception as exc:  # queue missing, folder wrong, auth — the run cannot continue
            out.error_type = "QUEUE_ERROR"
            out.error_message = redact(f"could not start a transaction on {input.queue_name} in {input.folder_path}: {exc}")
            break
        if transaction is None:
            break

        out.processed += 1
        key = str(transaction.get("Key"))  # logging only; completion is keyed by the numeric Id
        transaction_id = _transaction_id(transaction)
        record_id = str(transaction.get("Reference") or "").strip()
        reference = record_id or "<no reference>"

        if transaction_id is None:
            out.failed += 1
            out.errors.append(f"record {reference}: transaction {key} has no numeric Id; it cannot be completed and stays InProgress")
            continue

        if not record_id:
            result = ProcessInvoiceOutput(
                error_type="INVALID_INPUT",
                error_message="transaction has no Reference (expected the AP_Invoice record Id)",
            )
        else:
            result = _process_invoice(
                ProcessInvoiceInput(record_id=record_id, entity_name=input.entity_name),
                entity_id=entity_id,
                api_token=api_token,
            )

        if result.error_type:
            out.failed += 1
            message = redact(f"record {reference}: {result.error_type}: {result.error_message}")
            out.errors.append(message)
            try:
                _complete(
                    transaction_id,
                    {"IsSuccessful": False, "ProcessingException": {"Type": "BusinessException", "Reason": message[:1000]}},
                    input,
                )
            except Exception as complete_exc:
                out.errors.append(redact(f"record {reference}: could not mark transaction Failed: {complete_exc}"))
            continue

        out.matched += int(result.po_matched)
        out.approval_required += int(result.approval_required)
        try:
            _complete(
                transaction_id,
                {
                    "IsSuccessful": True,
                    "Output": {
                        FIELD_PO_MATCHED: result.po_matched,
                        FIELD_APPROVAL_NEEDED: result.approval_required,
                        "MatchReason": result.match_reason,
                    },
                },
                input,
            )
        except Exception as exc:
            # The record is already updated; report it so a facilitator can reconcile the queue.
            out.errors.append(redact(f"record {reference}: updated, but the transaction could not be marked Successful: {exc}"))

    return out


# --------------------------------------------------------------------------------------
# Function 4 — get_invoice_status (read-only wait-loop contract for Lab 10)
# --------------------------------------------------------------------------------------


class InvoiceStatusInput(BaseModel):
    record_id: str = ""
    entity_name: str = DEFAULT_ENTITY_NAME


class InvoiceStatusOutput(BaseModel):
    record_id: str = ""
    invoice_lifecycle_state: str = ""  # empty when unset or the field does not exist yet
    approval_needed: bool = True  # conservative when unset: a human decision is still expected
    posted_to_erp: bool = False
    reviewed_by: str = ""  # empty when unset or the field does not exist yet (Day 1 entities)
    reviewed_at: str = ""  # empty when unset or the field does not exist yet (Day 1 entities)
    found: bool = False
    error_type: str = ""
    error_message: str = ""


@traced(name="get_invoice_status", run_type="uipath")
def get_invoice_status(input: InvoiceStatusInput) -> InvoiceStatusOutput:
    """Read one AP_Invoice record's lifecycle fields. Performs no write of any kind."""
    record_id = input.record_id.strip()
    out = InvoiceStatusOutput(record_id=record_id)
    try:
        if not record_id:
            raise BusinessError("record_id is required", "INVALID_INPUT")
        try:
            # No required fields: the lifecycle/review fields are added by later labs.
            entity_id = _resolve_entity(input.entity_name, _entity_id_for(input.entity_name), required_fields=())
        except Exception as exc:
            raise BusinessError(str(exc), "ENTITY_RESOLUTION_FAILED") from exc

        data = _read_record(entity_id, record_id)
        out.found = True
        out.invoice_lifecycle_state = _to_text(_get_field(data, FIELD_LIFECYCLE_STATE))
        out.approval_needed = _to_bool(_get_field(data, FIELD_APPROVAL_NEEDED), default=True)
        out.posted_to_erp = _to_bool(_get_field(data, FIELD_POSTED_TO_ERP), default=False)
        out.reviewed_by = _to_text(_get_field(data, FIELD_REVIEWED_BY))
        out.reviewed_at = _to_text(_get_field(data, FIELD_REVIEWED_AT))
    except BusinessError as exc:
        out.error_type = exc.error_type
        out.error_message = redact(str(exc))
    except Exception as exc:
        out.error_type = "UNEXPECTED_ERROR"
        out.error_message = redact(f"{type(exc).__name__}: {exc}")
    return out
