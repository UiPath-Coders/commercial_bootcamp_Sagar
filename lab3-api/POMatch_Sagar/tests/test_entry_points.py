"""SDK entry points with a fake UiPath SDK: queue delegation, per-record idempotency, read-only status."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

import main

ENTITY_ID = "entity-1"
FIELDS = [SimpleNamespace(name=n) for n in main.REQUIRED_FIELDS + (main.FIELD_POSTED_TO_ERP, main.FIELD_LIFECYCLE_STATE)]


class FakeRecord:
    def __init__(self, data):
        self._data = data

    def model_dump(self, by_alias=True):
        return dict(self._data)


class FakeEntities:
    def __init__(self, records):
        self.records = records
        self.updates = []

    def retrieve_by_name(self, name):
        return SimpleNamespace(id=ENTITY_ID, name=name, fields=FIELDS)

    def get_record(self, entity_id, record_id):
        if record_id not in self.records:
            raise RuntimeError("404 Not Found")
        return FakeRecord(self.records[record_id])

    def update_record(self, entity_id, record_id, data):
        self.updates.append((record_id, data))
        self.records[record_id].update(data)


class FakeQueues:
    def __init__(self, references):
        self.pending = [{"Id": i + 1, "Key": f"k{i + 1}", "Reference": ref} for i, ref in enumerate(references)]
        self.results = {}

    def create_transaction_item(self, item, queue_name, no_robot, folder_path):
        assert folder_path == main.DEFAULT_FOLDER_PATH
        if not self.pending:
            raise json.JSONDecodeError("Expecting value", "", 0)  # 204: queue empty
        return self.pending.pop(0)

    def complete_transaction_item(self, transaction_id, result, queue_name, folder_path):
        self.results[int(transaction_id)] = result
        raise json.JSONDecodeError("Expecting value", "", 0)  # empty 200 body = success


def invoice(po_number="PO-2026-0431", total=4155.40, **extra):
    return {"VendorName": "Northwind Office Supplies", "PoNumber": po_number, "TotalAmount": total, "Currency": "USD", **extra}


@pytest.fixture
def fake_sdk(monkeypatch):
    def install(records=None, references=()):
        fake = SimpleNamespace(entities=FakeEntities(records or {}), queues=FakeQueues(references))
        monkeypatch.setattr(main, "sdk", lambda: fake)
        return fake

    return install


@pytest.fixture
def erp_found(mock_erp):
    mock_erp(lambda request: httpx.Response(200, json={"po": {"found": True, "vendorActive": True, "openAmount": 4200.0, "currency": "USD"}}))


def test_queue_delegates_every_transaction_to_process_invoice(fake_sdk, monkeypatch):
    fake = fake_sdk(references=["r1", "r2", "r3"])
    calls = []

    def fake_process(input, entity_id=None):
        calls.append((input.record_id, input.entity_name, entity_id))
        if input.record_id == "r2":
            return main.ProcessInvoiceOutput(record_id="r2", error_type="PO_LOOKUP_FAILED", error_message="boom")
        return main.ProcessInvoiceOutput(record_id=input.record_id, po_matched=True, approval_required=input.record_id == "r3")

    monkeypatch.setattr(main, "_process_invoice", fake_process)
    out = main.process_invoice_queue(main.ProcessQueueInput())

    assert calls == [(r, "AP_Invoice_Sagar", ENTITY_ID) for r in ("r1", "r2", "r3")]
    assert (out.processed, out.matched, out.approval_required, out.failed) == (3, 2, 1, 1)
    assert fake.queues.results[1]["IsSuccessful"] is True
    assert fake.queues.results[2]["IsSuccessful"] is False
    assert fake.queues.results[2]["ProcessingException"]["Type"] == "BusinessException"
    assert fake.queues.results[3]["IsSuccessful"] is True


def test_queue_respects_max_items(fake_sdk, monkeypatch):
    fake = fake_sdk(references=["r1", "r2", "r3"])
    monkeypatch.setattr(main, "_process_invoice", lambda input, entity_id=None: main.ProcessInvoiceOutput(record_id=input.record_id))
    out = main.process_invoice_queue(main.ProcessQueueInput(max_items=2))
    assert out.processed == 2 and len(fake.queues.pending) == 1


def test_process_invoice_writes_schema_names_and_is_idempotent(fake_sdk, erp_found):
    fake = fake_sdk(records={"r1": invoice()})
    first = main.process_invoice(main.ProcessInvoiceInput(record_id="r1"))
    second = main.process_invoice(main.ProcessInvoiceInput(record_id="r1"))
    assert first == second
    assert (first.po_matched, first.approval_required, first.match_reason, first.error_type) == (True, False, "MATCHED", "")
    assert fake.entities.updates == [("r1", {"POMatched": True, "ApprovalNeeded": False})]  # second run: no write


def test_process_invoice_does_not_write_when_the_lookup_fails(fake_sdk, mock_erp):
    fake = fake_sdk(records={"r1": invoice()})
    mock_erp(lambda request: httpx.Response(500, text="down"))
    out = main.process_invoice(main.ProcessInvoiceInput(record_id="r1"))
    assert out.error_type == "ERP_HTTP_ERROR" and out.po_matched is False and out.approval_required is True
    assert fake.entities.updates == []


def test_process_invoice_missing_record(fake_sdk):
    fake_sdk(records={})
    assert main.process_invoice(main.ProcessInvoiceInput(record_id="nope")).error_type == "RECORD_NOT_FOUND"


def test_get_invoice_status_performs_no_write(fake_sdk, monkeypatch):
    fake = fake_sdk(records={"r1": invoice(InvoiceLifecycleState="READY_FOR_APPROVAL", ApprovalNeeded=True, PostedToERP=False)})
    monkeypatch.setattr(main, "_write_po_result", lambda *a, **k: pytest.fail("get_invoice_status must not write"))
    out = main.get_invoice_status(main.InvoiceStatusInput(record_id="r1"))
    assert fake.entities.updates == []
    assert out.found is True and out.invoice_lifecycle_state == "READY_FOR_APPROVAL"
    assert out.approval_needed is True and out.posted_to_erp is False


def test_get_invoice_status_defaults_for_unset_and_missing_fields(fake_sdk):
    fake_sdk(records={"r1": invoice()})  # no lifecycle, approval, posted or review fields
    out = main.get_invoice_status(main.InvoiceStatusInput(record_id="r1"))
    assert out.model_dump() == {
        "record_id": "r1", "invoice_lifecycle_state": "", "approval_needed": True, "posted_to_erp": False,
        "reviewed_by": "", "reviewed_at": "", "found": True, "error_type": "", "error_message": "",
    }


def test_queue_run_level_failure_sets_error_fields(fake_sdk, monkeypatch):
    fake_sdk(references=["r1"])
    monkeypatch.setattr(main, "_next_transaction", lambda q, f: (_ for _ in ()).throw(RuntimeError("404 Queue missing")))
    out = main.process_invoice_queue(main.ProcessQueueInput())
    assert out.error_type == "QUEUE_ERROR" and "404 Queue missing" in out.error_message
    assert out.processed == 0 and out.errors == []


def test_queue_unresolvable_entity_stops_before_the_queue(fake_sdk, monkeypatch):
    fake = fake_sdk(references=["r1"])
    monkeypatch.setattr(fake.entities, "retrieve_by_name", lambda name: (_ for _ in ()).throw(RuntimeError("404")))
    out = main.process_invoice_queue(main.ProcessQueueInput())
    assert out.error_type == "ENTITY_RESOLUTION_FAILED" and out.processed == 0
    assert len(fake.queues.pending) == 1  # nothing taken from the queue


def test_queue_reports_an_updated_record_whose_transaction_could_not_complete(fake_sdk, monkeypatch):
    fake = fake_sdk(references=["r1"])
    monkeypatch.setattr(main, "_process_invoice", lambda input, entity_id=None: main.ProcessInvoiceOutput(record_id="r1", po_matched=True))
    monkeypatch.setattr(fake.queues, "complete_transaction_item", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("503")))
    out = main.process_invoice_queue(main.ProcessQueueInput())
    assert out.failed == 0 and out.errors == ["record r1: updated, but the transaction could not be marked Successful: 503"]
