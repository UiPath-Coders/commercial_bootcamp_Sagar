"""process_invoice_queue with the UiPath SDK replaced by an in-memory fake and the ERP mocked.

This proves the orchestration (Reference -> record -> po_lookup -> record -> transaction status)
against the SDK method signatures found in uipath 2.14.x. What it cannot prove is the behaviour of
a real tenant (auth, Data Fabric partial updates, Orchestrator StartTransaction semantics); see the
README section "What was not verified offline".
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from uipath.platform.entities.entities import EntityRecord

import main
from main import ProcessQueueInput, process_invoice_queue

ENTITY_ID = "11111111-2222-3333-4444-555555555555"
ALL_FIELDS = ["Id", "VendorName", "VendorTaxId", "InvoiceNumber", "PONumber", "TotalAmount", "Currency", "POMatched", "ApprovalNeeded", "PostedToERP"]

# Same answers as mock-erp/data/purchase-orders.json for the POs used below.
ERP_FIXTURE = {
    "PO-2026-0431": {"found": True, "vendorActive": True, "openAmount": 4200.0, "currency": "USD"},
    "PO-2026-0447": {"found": True, "vendorActive": True, "openAmount": 12740.0, "currency": "USD"},
    "PO-2026-0461": {"found": True, "vendorActive": False, "openAmount": 2954.0, "currency": "USD"},
}
ERP_DEFAULT = {"found": False, "vendorActive": False, "openAmount": 0, "currency": "USD"}


class FakeQueues:
    """Behaves like Orchestrator behind uipath 2.14.x's QueuesService.

    ``complete_transaction_item`` is keyed by the numeric transaction Id (``Queues({Id})/
    SetTransactionResult``): a GUID Key answers 404. A successful call answers 200 with an EMPTY
    body, so the SDK's ``response.json()`` raises ``json.JSONDecodeError`` even though the result
    was stored; ``empty_body=False`` returns ``{}`` instead.
    """

    def __init__(self, transactions, empty_body=True):
        self.pending = list(transactions)
        self.started = []
        self.completed = []  # (transaction id, result, queue_name, folder_path)
        self.empty_body = empty_body

    def create_transaction_item(self, item, queue_name=None, no_robot=False, *, folder_key=None, folder_path=None):
        self.started.append((item, queue_name, folder_path, no_robot))
        if not self.pending:
            # what httpx.Response.json() does on Orchestrator's 204 No Content
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self.pending.pop(0)

    def complete_transaction_item(self, transaction_key, result, queue_name=None, *, folder_key=None, folder_path=None):
        if not str(transaction_key).isdigit():
            request = httpx.Request("POST", f"https://cloud.test/orchestrator_/odata/Queues({transaction_key})/UiPathODataSvc.SetTransactionResult")
            raise httpx.HTTPStatusError("404 Not Found", request=request, response=httpx.Response(404, request=request))
        self.completed.append((int(transaction_key), result, queue_name, folder_path))
        if self.empty_body:
            raise json.JSONDecodeError("Expecting value", "", 0)  # 200 with an empty body
        return {}


class FakeEntities:
    def __init__(self, records, field_names=ALL_FIELDS, entity_name="AP_Invoice_Reference"):
        self.records = {rid: dict(data) for rid, data in records.items()}
        self.entity = SimpleNamespace(id=ENTITY_ID, name=entity_name, fields=[SimpleNamespace(name=n) for n in field_names])
        self.lookups = []
        self.updates = []  # (entity_key, record_id, data)
        self.fail_update_for = set()

    def retrieve_by_name(self, entity_name, folder_key=None):
        self.lookups.append(("by_name", entity_name))
        if entity_name != self.entity.name:
            raise RuntimeError(f"404 entity {entity_name} not found")
        return self.entity

    def retrieve(self, entity_key):
        self.lookups.append(("by_id", entity_key))
        if entity_key != self.entity.id:
            raise RuntimeError(f"404 entity {entity_key} not found")
        return self.entity

    def get_record(self, entity_key, record_id, expansion_level=None):
        assert entity_key == ENTITY_ID
        if record_id not in self.records:
            raise RuntimeError(f"404 record {record_id} not found")
        return EntityRecord.model_validate({"Id": record_id, **self.records[record_id]})

    def update_record(self, entity_key, record_id, data, expansion_level=None):
        assert entity_key == ENTITY_ID
        if record_id in self.fail_update_for:
            raise RuntimeError("403 forbidden")
        self.records[record_id].update(data)
        self.updates.append((entity_key, record_id, dict(data)))
        return EntityRecord.model_validate({"Id": record_id, **self.records[record_id]})


class FakeAssets:
    def __init__(self, values=None):
        self.values = values or {}
        self.retrieved = []

    def retrieve(self, name, *, folder_path=None, folder_key=None):
        self.retrieved.append((name, folder_path))
        if name not in self.values:
            raise RuntimeError(f"404 asset {name} not found")
        return SimpleNamespace(secret_value=self.values[name], string_value=None, value=None, credential_password=None)

def tx_id(key: str) -> int:
    """Deterministic numeric transaction Id for a test Key: k1 -> 1001, k2 -> 1002, ..."""
    return 1000 + int(key.lstrip("k"))


def tx(key: str, reference: str | None):
    item = {"Id": tx_id(key), "Key": f"00000000-0000-0000-0000-{tx_id(key):012d}", "Status": "InProgress", "SpecificContent": {}}
    if reference is not None:
        item["Reference"] = reference
    return item


def record(vendor, po, total, currency="USD"):
    return {"VendorName": vendor, "VendorTaxId": "00-0000000", "InvoiceNumber": f"INV-{po[-4:]}", "PONumber": po, "TotalAmount": total, "Currency": currency, "POMatched": None, "ApprovalNeeded": None, "PostedToERP": None}


@pytest.fixture
def fake_sdk(monkeypatch):
    def install(queues: FakeQueues, entities: FakeEntities, assets: FakeAssets | None = None):
        monkeypatch.setattr(main, "_sdk", SimpleNamespace(queues=queues, entities=entities, assets=assets or FakeAssets()))
        return queues, entities

    return install


@pytest.fixture(autouse=True)
def erp(mock_erp):
    calls = []

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        calls.append(body)
        if body.get("poNumber") == "PO-BROKEN":
            return httpx.Response(500, text="erp down")
        return httpx.Response(200, json={"po": ERP_FIXTURE.get(str(body.get("poNumber", "")).upper(), ERP_DEFAULT)})

    mock_erp(handler)
    return calls


def test_happy_path_updates_records_and_completes_transactions(fake_sdk, erp):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-001"), tx("k2", "rec-002"), tx("k3", "rec-005"), tx("k4", "rec-010")]),
        FakeEntities(
            {
                "rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40),
                "rec-002": record("Contoso Logistics", "PO-2026-0447", 12740.00),
                "rec-005": record("Blue Harbor Catering", "PO-2026-0461", 2954.00),
                "rec-010": record("Pacific Timber Company", "PO-2026-0489", 9902.58),
            }
        ),
    )

    out = process_invoice_queue(ProcessQueueInput())

    assert out.error_type == "" and out.errors == []
    assert (out.processed, out.matched, out.approval_required, out.failed) == (4, 2, 3, 0)

    # records: POMatched / ApprovalNeeded written with the exact system names, nothing else touched
    assert entities.updates == [
        (ENTITY_ID, "rec-001", {"POMatched": True, "ApprovalNeeded": False}),
        (ENTITY_ID, "rec-002", {"POMatched": True, "ApprovalNeeded": True}),
        (ENTITY_ID, "rec-005", {"POMatched": False, "ApprovalNeeded": True}),
        (ENTITY_ID, "rec-010", {"POMatched": False, "ApprovalNeeded": True}),
    ]
    assert entities.records["rec-001"]["VendorTaxId"] == "00-0000000"  # untouched

    # the ERP request was filled from the record, with the samplepolookup.md field mapping
    assert erp[0] == {"vendorName": "Northwind Office Supplies", "poNumber": "PO-2026-0431", "invoiceTotal": 4155.40, "currency": "USD"}

    # every transaction marked Successful on the configured queue/folder, with a useful Output
    # completed by the numeric transaction Id, never by the GUID Key (which Orchestrator 404s)
    assert [c[0] for c in queues.completed] == [1001, 1002, 1003, 1004]
    assert all(c[1]["IsSuccessful"] is True for c in queues.completed)
    assert all((c[2], c[3]) == ("InvoiceQueue_Reference", "Agentic Bootcamp/APAutomation_Reference") for c in queues.completed)
    assert queues.completed[2][1]["Output"] == {"POMatched": False, "ApprovalNeeded": True, "MatchReason": "VENDOR_INACTIVE"}

    # entity resolved by name (default input), queue drained until the 204
    assert entities.lookups == [("by_name", "AP_Invoice_Reference")]
    assert len(queues.started) == 5


def test_missing_record_marks_transaction_failed_and_continues(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-missing"), tx("k2", "rec-001")]),
        FakeEntities({"rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40)}),
    )
    out = process_invoice_queue(ProcessQueueInput())

    assert (out.processed, out.matched, out.approval_required, out.failed) == (2, 1, 0, 1)
    assert len(out.errors) == 1 and "rec-missing" in out.errors[0]

    transaction_id, result, *_ = queues.completed[0]
    assert transaction_id == 1001
    assert result["IsSuccessful"] is False
    assert result["ProcessingException"]["Type"] == "BusinessException"
    assert "rec-missing" in result["ProcessingException"]["Reason"]
    assert queues.completed[1][1]["IsSuccessful"] is True
    assert [u[1] for u in entities.updates] == ["rec-001"]


def test_transaction_without_reference_fails_cleanly(fake_sdk):
    queues, entities = fake_sdk(FakeQueues([tx("k1", None), tx("k2", "")]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())
    assert (out.processed, out.failed) == (2, 2)
    assert all("no Reference" in e for e in out.errors)
    assert all(c[1]["IsSuccessful"] is False for c in queues.completed)
    assert entities.updates == []


def test_erp_failure_does_not_write_a_guess_to_the_record(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-x")]),
        FakeEntities({"rec-x": record("Some Vendor", "PO-BROKEN", 100.0)}),
    )
    out = process_invoice_queue(ProcessQueueInput())
    assert (out.processed, out.failed, out.matched, out.approval_required) == (1, 1, 0, 0)
    assert "ERP_HTTP_ERROR" in out.errors[0] and "rec-x" in out.errors[0]
    assert entities.updates == []
    assert entities.records["rec-x"]["POMatched"] is None
    assert queues.completed[0][1]["IsSuccessful"] is False


def test_bad_total_amount_is_a_business_exception(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-a"), tx("k2", "rec-b")]),
        FakeEntities({"rec-a": record("V", "PO-2026-0431", None), "rec-b": record("V", "PO-2026-0431", "n/a")}),
    )
    out = process_invoice_queue(ProcessQueueInput())
    assert out.failed == 2
    assert "TotalAmount is empty" in out.errors[0]
    assert "TotalAmount is not numeric" in out.errors[1]


def test_record_update_failure_marks_transaction_failed(fake_sdk):
    entities = FakeEntities({"rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40)})
    entities.fail_update_for.add("rec-001")
    queues, _ = fake_sdk(FakeQueues([tx("k1", "rec-001")]), entities)
    out = process_invoice_queue(ProcessQueueInput())
    assert out.failed == 1 and "could not be updated" in out.errors[0]
    assert queues.completed[0][1]["IsSuccessful"] is False


def test_max_items_is_respected(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx(f"k{i}", "rec-001") for i in range(5)]),
        FakeEntities({"rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40)}),
    )
    out = process_invoice_queue(ProcessQueueInput(max_items=2))
    assert out.processed == 2
    assert len(queues.pending) == 3  # left in the queue for the next run
    assert len(queues.started) == 2  # no extra GetNext past the limit


def test_empty_queue_processes_zero(fake_sdk):
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())
    assert out.model_dump() == {"processed": 0, "matched": 0, "approval_required": 0, "failed": 0, "errors": [], "error_type": "", "error_message": ""}


def test_entity_missing_lab3_fields_stops_before_touching_the_queue(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-001")]),
        FakeEntities({"rec-001": record("V", "PO-2026-0431", 1.0)}, field_names=["Id", "VendorName", "PONumber", "TotalAmount", "Currency", "PO Matched"]),
    )
    out = process_invoice_queue(ProcessQueueInput())
    assert out.error_type == "ENTITY_RESOLUTION_FAILED"
    assert "POMatched" in out.error_message and "ApprovalNeeded" in out.error_message
    assert out.processed == 0 and queues.started == []


def test_unknown_entity_name_is_reported(fake_sdk):
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput(entity_name="AP_Invoice_Nobody"))
    assert out.error_type == "ENTITY_RESOLUTION_FAILED" and "AP_Invoice_Nobody" in out.error_message


def test_entity_id_input_skips_lookup_by_name(fake_sdk):
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput(entity_id=ENTITY_ID))
    assert out.error_type == ""
    assert entities.lookups == [("by_id", ENTITY_ID)]


def test_custom_queue_and_folder_are_passed_to_the_sdk(fake_sdk):
    queues, entities = fake_sdk(
        FakeQueues([tx("k1", "rec-001")]),
        FakeEntities({"rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40)}, entity_name="AP_Invoice_Axel"),
    )
    out = process_invoice_queue(ProcessQueueInput(queue_name="InvoiceQueue_Axel", folder_path="APAutomation_Axel", entity_name="AP_Invoice_Axel"))
    assert out.processed == 1 and out.failed == 0
    assert queues.started[0][1:3] == ("InvoiceQueue_Axel", "APAutomation_Axel")
    assert queues.completed[0][2:] == ("InvoiceQueue_Axel", "APAutomation_Axel")


def test_hosted_token_is_read_from_the_named_asset_without_becoming_function_input(fake_sdk, monkeypatch):
    monkeypatch.delenv("ERP_API_TOKEN", raising=False)
    assets = FakeAssets({"MockERPAccessToken_Axel": "signed-token-from-secret-asset"})
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({}), assets)
    out = process_invoice_queue(ProcessQueueInput(erp_api_token_asset_name="MockERPAccessToken_Axel"))
    assert out.error_type == ""
    assert assets.retrieved == [("MockERPAccessToken_Axel", "Agentic Bootcamp/APAutomation_Reference")]


def test_missing_hosted_token_asset_stops_before_entity_or_queue_work(fake_sdk, monkeypatch):
    monkeypatch.delenv("ERP_API_TOKEN", raising=False)
    queues, entities = fake_sdk(FakeQueues([]), FakeEntities({}), FakeAssets())
    out = process_invoice_queue(ProcessQueueInput(erp_api_token_asset_name="MissingToken"))
    assert out.error_type == "ERP_AUTH_CONFIGURATION_FAILED"
    assert "MissingToken" in out.error_message
    assert entities.lookups == [] and queues.started == []


def test_queue_error_is_fatal_and_reported(fake_sdk):
    class BrokenQueues(FakeQueues):
        def create_transaction_item(self, *a, **k):
            raise RuntimeError("404 Queue InvoiceQueue_Reference does not exist")

    queues, entities = fake_sdk(BrokenQueues([]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())
    assert out.error_type == "QUEUE_ERROR" and "does not exist" in out.error_message
    assert out.processed == 0


def test_only_a_json_decode_error_means_empty_queue(fake_sdk):
    """A plain ValueError (e.g. the SDK's 'Robot key is not set') must surface, not look like an empty queue."""

    class NoRobotQueues(FakeQueues):
        def create_transaction_item(self, *a, **k):
            raise ValueError("Robot key is not set (UIPATH_ROBOT_KEY)")

    queues, entities = fake_sdk(NoRobotQueues([]), FakeEntities({}))
    out = process_invoice_queue(ProcessQueueInput())
    assert out.error_type == "QUEUE_ERROR" and "Robot key" in out.error_message


def test_robot_association_follows_uipath_robot_key(fake_sdk, monkeypatch):
    records = {"rec-001": record("Northwind Office Supplies", "PO-2026-0431", 4155.40)}

    monkeypatch.delenv("UIPATH_ROBOT_KEY", raising=False)  # local run: no robot to associate
    queues, _ = fake_sdk(FakeQueues([tx("k1", "rec-001")]), FakeEntities(records))
    process_invoice_queue(ProcessQueueInput())
    assert queues.started[0][3] is True  # no_robot=True

    monkeypatch.setenv("UIPATH_ROBOT_KEY", "robot-key-set-by-the-serverless-job")
    queues, _ = fake_sdk(FakeQueues([tx("k1", "rec-001")]), FakeEntities(records))
    process_invoice_queue(ProcessQueueInput())
    assert queues.started[0][3] is False  # associate the transaction with the running robot


def test_default_names_follow_the_reference_suffix():
    defaults = ProcessQueueInput()
    assert defaults.queue_name == "InvoiceQueue_Reference"
    assert defaults.folder_path == "Agentic Bootcamp/APAutomation_Reference"
    assert defaults.entity_name == "AP_Invoice_Reference"
    assert defaults.erp_api_token_asset_name == ""
    assert defaults.max_items == 50
