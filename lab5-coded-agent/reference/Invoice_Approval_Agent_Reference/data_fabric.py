"""Data Fabric I/O for the reference agent (UiPath Python SDK).

Two functions cross the I/O boundary and both are ``@mockable`` so the UiPath
evaluation runner (``uip codedagent eval`` with a ``mockito`` mocking strategy)
and pytest can replace them:

* ``read_invoice_record(entity_name, record_id)``  -> record dict
* ``write_agent_outputs(entity_name, record_id, fields)`` -> updated record dict

The entity is tenant-scoped, so no folder key/path is passed anywhere.
``AP_Invoice_<user_name>`` is resolved by name to its entity Id once per call
(or taken from ``AP_INVOICE_ENTITY_ID`` when set).

Offline mode: when ``AP_INVOICE_FIXTURE_FILE`` points at a CSV (for example
``lab-assets/vendor-invoice/seeds/data-fabric-input.csv``) or a JSON file, the
record is read from that file (``InvoiceReference`` or ``Id`` acts as the
record Id) and the six output fields are written to
``<AP_INVOICE_FIXTURE_OUTPUT_DIR>/<recordId>.json`` instead of the tenant.
This lets facilitators run ``uip codedagent run`` without a tenant.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from uipath.eval.mocks import mockable

from config import Settings, load_settings

# The six fields this agent owns on the record. Nothing else is ever written.
AGENT_OUTPUT_FIELDS: tuple[str, ...] = (
    "ApprovalEvidenceState",
    "MissingApprovalFields",
    "AgentRecommendation",
    "ApprovalPackageJson",
    "AgentProcessedAt",
    "InvoiceLifecycleState",
)


class RecordNotFoundError(LookupError):
    """Raised when the record Id does not exist in the entity (or fixture)."""


# --------------------------------------------------------------------------- #
# Tenant-backed implementation (UiPath Python SDK)
# --------------------------------------------------------------------------- #
def _sdk():
    # Imported and instantiated lazily: `uip codedagent init` imports this module
    # without credentials, and module-level UiPath() would fail there.
    from uipath.platform import UiPath

    return UiPath()


def resolve_entity_id(settings: Settings, sdk=None) -> str:
    """Return the entity Id for the configured entity name (tenant scope, no folder)."""
    if settings.entity_id:
        return settings.entity_id
    sdk = sdk or _sdk()
    entity = sdk.entities.retrieve_by_name(settings.entity_name)  # no folder_key: tenant-scoped
    return entity.id


def _read_from_tenant(settings: Settings, record_id: str) -> dict[str, Any]:
    sdk = _sdk()
    entity_id = resolve_entity_id(settings, sdk)
    record = sdk.entities.get_record(entity_id, record_id)
    return record.model_dump(by_alias=True)


def _write_to_tenant(settings: Settings, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    sdk = _sdk()
    entity_id = resolve_entity_id(settings, sdk)
    # update_record (single record) fires Data Fabric triggers, unlike the batch call.
    updated = sdk.entities.update_record(entity_id, record_id, fields)
    return updated.model_dump(by_alias=True)


# --------------------------------------------------------------------------- #
# Fixture-backed implementation (offline)
# --------------------------------------------------------------------------- #
def _load_fixture(path: str) -> dict[str, dict[str, Any]]:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"Fixture file not found: {file}")
    if file.suffix.lower() == ".csv":
        with file.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        records: dict[str, dict[str, Any]] = {}
        for row in rows:
            record_id = row.get("Id") or row.get("InvoiceReference")
            if not record_id:
                continue
            clean = {key: (value if value != "" else None) for key, value in row.items()}
            clean["Id"] = record_id
            records[record_id] = clean
        return records
    data = json.loads(file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {item["Id"]: item for item in data}
    return data


def _read_from_fixture(settings: Settings, record_id: str) -> dict[str, Any]:
    records = _load_fixture(settings.fixture_file or "")
    if record_id not in records:
        raise RecordNotFoundError(f"Record {record_id!r} not found in fixture {settings.fixture_file}")
    return dict(records[record_id])


def _write_to_fixture(settings: Settings, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    record = _read_from_fixture(settings, record_id)
    record.update(fields)
    out_dir = Path(settings.fixture_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{record_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


# --------------------------------------------------------------------------- #
# Public, mockable boundary
# --------------------------------------------------------------------------- #
@mockable()
def read_invoice_record(entity_name: str, record_id: str) -> dict[str, Any]:
    """Read one AP_Invoice record by Id and return it as a dict keyed by system field name."""
    settings = load_settings(entity_name)
    if settings.offline:
        return _read_from_fixture(settings, record_id)
    return _read_from_tenant(settings, record_id)


@mockable()
def write_agent_outputs(entity_name: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Write the six agent output fields back to the same record and return the updated record."""
    unexpected = sorted(set(fields) - set(AGENT_OUTPUT_FIELDS))
    if unexpected:
        raise ValueError(f"Refusing to write non-agent fields to the record: {unexpected}")
    settings = load_settings(entity_name)
    if settings.offline:
        return _write_to_fixture(settings, record_id, fields)
    return _write_to_tenant(settings, record_id, fields)


def describe_backend() -> str:
    """Human-readable description of where reads/writes go (for logs and the package)."""
    settings = load_settings()
    if settings.offline:
        return f"fixture:{os.path.basename(settings.fixture_file or '')}"
    return f"data-fabric:{settings.entity_name}"
