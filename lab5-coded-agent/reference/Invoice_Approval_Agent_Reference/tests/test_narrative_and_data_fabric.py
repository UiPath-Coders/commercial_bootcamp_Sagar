"""Boundary modules: narrative fallback behaviour and Data Fabric I/O (SDK faked, fixture mode real)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import data_fabric
import narrative
from conftest import SEED_CSV
from data_fabric import AGENT_OUTPUT_FIELDS, RecordNotFoundError, read_invoice_record, write_agent_outputs

FACTS = {
    "VendorName": "Northwind Office Supplies Inc.",
    "InvoiceNumber": "TRAIN-NW-1001",
    "PONumber": "PO-2026-0501",
    "TotalAmount": 14850.0,
    "Currency": "USD",
    "GLAccount": "6120-Office Supplies",
    "CostCenter": "CC-410 Facilities",
    "Approver": "Jordan Example",
    "PaymentTerms": "Net 30",
    "VendorRiskScore": "Medium",
    "ReceiptReference": "GR-2026-0501-01",
    "InvoiceLineSummary": "Ergonomic chairs x25; standing desks x10",
}


class TestNarrative:
    def test_template_mode_never_touches_the_gateway(self, monkeypatch):
        monkeypatch.setenv("AP_INVOICE_NARRATIVE_MODE", "template")
        monkeypatch.setattr(narrative, "_llm_narrative", lambda *_: pytest.fail("LLM must not be called"))
        result = narrative.generate_narrative(FACTS)
        assert result["source"] == "template"
        assert "Northwind" in result["summary"] and "PO-2026-0501" in result["summary"]
        assert result["risk_flags"] == ["Vendor risk score is Medium"]

    def test_llm_mode_uses_the_gateway_result(self, monkeypatch):
        monkeypatch.setenv("AP_INVOICE_NARRATIVE_MODE", "llm")
        monkeypatch.setenv("AP_INVOICE_LLM_MODEL", "fake-model")
        seen = {}

        def fake_llm(facts, model_name):
            seen["model"] = model_name
            return {"summary": "LLM says ok", "risk_flags": [], "confidence": "high", "source": "llm", "model": model_name, "reason": None}

        monkeypatch.setattr(narrative, "_llm_narrative", fake_llm)
        result = narrative.generate_narrative(FACTS)
        assert result["source"] == "llm" and result["summary"] == "LLM says ok"
        assert seen["model"] == "fake-model"

    def test_llm_failure_falls_back_to_template_and_records_the_reason(self, monkeypatch):
        monkeypatch.setenv("AP_INVOICE_NARRATIVE_MODE", "llm")

        def boom(*_):
            raise ConnectionError("gateway unreachable")

        monkeypatch.setattr(narrative, "_llm_narrative", boom)
        result = narrative.generate_narrative(FACTS)
        assert result["source"] == "template"
        assert "ConnectionError" in result["reason"]

    def test_invalid_mode_is_rejected(self, monkeypatch):
        monkeypatch.setenv("AP_INVOICE_NARRATIVE_MODE", "sometimes")
        with pytest.raises(ValueError):
            narrative.generate_narrative(FACTS)

    def test_narrative_input_whitelist(self):
        facts = narrative.narrative_input({**FACTS, "Id": "rec-1", "VendorTaxId": "00-0", "ApprovalPackageJson": "{}"})
        assert "Id" not in facts and "VendorTaxId" not in facts and "ApprovalPackageJson" not in facts
        assert facts["VendorName"] == FACTS["VendorName"]


class FakeEntitiesService:
    def __init__(self):
        self.calls = []
        self.record = {"Id": "rec-1", "POMatched": True, "ApprovalNeeded": False}

    def retrieve_by_name(self, entity_name, folder_key=None):
        self.calls.append(("retrieve_by_name", entity_name, folder_key))
        return SimpleNamespace(id="entity-guid-1", name=entity_name)

    def get_record(self, entity_key, record_id, expansion_level=None):
        self.calls.append(("get_record", entity_key, record_id))
        return SimpleNamespace(model_dump=lambda by_alias=True: dict(self.record))

    def update_record(self, entity_key, record_id, data, expansion_level=None):
        self.calls.append(("update_record", entity_key, record_id, data))
        merged = {**self.record, **data}
        return SimpleNamespace(model_dump=lambda by_alias=True: merged)


class TestDataFabricTenantPath:
    @pytest.fixture
    def fake_sdk(self, monkeypatch):
        entities = FakeEntitiesService()
        monkeypatch.setattr(data_fabric, "_sdk", lambda: SimpleNamespace(entities=entities))
        return entities

    def test_read_resolves_entity_by_name_at_tenant_scope(self, fake_sdk):
        record = read_invoice_record("AP_Invoice_Reference", "rec-1")
        assert record["Id"] == "rec-1"
        assert fake_sdk.calls[0] == ("retrieve_by_name", "AP_Invoice_Reference", None)  # no folder key
        assert fake_sdk.calls[1] == ("get_record", "entity-guid-1", "rec-1")

    def test_write_uses_single_record_update_on_the_same_id(self, fake_sdk):
        fields = {name: "x" for name in AGENT_OUTPUT_FIELDS}
        updated = write_agent_outputs("AP_Invoice_Reference", "rec-1", fields)
        assert fake_sdk.calls[-1] == ("update_record", "entity-guid-1", "rec-1", fields)
        assert updated["AgentRecommendation"] == "x"

    def test_entity_id_env_skips_name_resolution(self, fake_sdk, monkeypatch):
        monkeypatch.setenv("AP_INVOICE_ENTITY_ID", "entity-guid-from-env")
        read_invoice_record("AP_Invoice_Reference", "rec-1")
        assert fake_sdk.calls == [("get_record", "entity-guid-from-env", "rec-1")]

    def test_write_refuses_fields_the_agent_does_not_own(self, fake_sdk):
        with pytest.raises(ValueError, match="Status"):
            write_agent_outputs("AP_Invoice_Reference", "rec-1", {"Status": "APPROVED", "AgentRecommendation": "x"})
        assert fake_sdk.calls == []


class TestDataFabricFixtureMode:
    @pytest.fixture
    def fixture_env(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("AP_INVOICE_FIXTURE_FILE", str(SEED_CSV))
        monkeypatch.setenv("AP_INVOICE_FIXTURE_OUTPUT_DIR", str(tmp_path / "out"))
        monkeypatch.setattr(data_fabric, "_sdk", lambda: pytest.fail("SDK must not be used in fixture mode"))
        return tmp_path / "out"

    def test_reads_seed_csv_rows_by_invoice_reference(self, fixture_env):
        record = read_invoice_record("AP_Invoice_Reference", "AP-TRAIN-1005")
        assert record["Id"] == "AP-TRAIN-1005"
        assert record["POMatched"] == "True"  # CSV text; the gates normalise it
        assert record["GLAccount"] is None and record["Approver"] is None

    def test_unknown_record_raises(self, fixture_env):
        with pytest.raises(RecordNotFoundError):
            read_invoice_record("AP_Invoice_Reference", "AP-TRAIN-9999")

    def test_writes_go_to_the_output_dir_not_the_seed_file(self, fixture_env):
        before = SEED_CSV.read_bytes()
        fields = {name: "x" for name in AGENT_OUTPUT_FIELDS}
        write_agent_outputs("AP_Invoice_Reference", "AP-TRAIN-1003", fields)
        assert SEED_CSV.read_bytes() == before
        written = json.loads((fixture_env / "AP-TRAIN-1003.json").read_text())
        assert written["AgentRecommendation"] == "x" and written["VendorName"] == "Meridian Cloud Services Corp."

    def test_describe_backend(self, fixture_env):
        assert data_fabric.describe_backend() == "fixture:data-fabric-input.csv"
