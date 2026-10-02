"""End-to-end graph tests with the SDK and the LLM mocked out."""

from __future__ import annotations

import json
from typing import Any

import pytest

import main
from conftest import case_to_record, load_decision_cases
from data_fabric import AGENT_OUTPUT_FIELDS

CASES = load_decision_cases()


class FakeBoundary:
    """Stands in for Data Fabric + LLM; records every call the graph makes."""

    def __init__(self, records: dict[str, dict[str, Any]]):
        self.records = records
        self.reads: list[tuple[str, str]] = []
        self.writes: list[tuple[str, str, dict[str, Any]]] = []
        self.narratives: list[dict[str, Any]] = []
        self.call_order: list[str] = []

    def read_invoice_record(self, entity_name: str, record_id: str) -> dict[str, Any]:
        self.call_order.append("read")
        self.reads.append((entity_name, record_id))
        return dict(self.records[record_id])

    def write_agent_outputs(self, entity_name: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.call_order.append("write")
        self.writes.append((entity_name, record_id, fields))
        return {**self.records[record_id], **fields}

    def generate_narrative(self, facts: dict[str, Any]) -> dict[str, Any]:
        self.call_order.append("llm")
        self.narratives.append(facts)
        return {"summary": "mock narrative", "risk_flags": [], "confidence": "high", "source": "mock", "model": "mock", "reason": None}


@pytest.fixture
def boundary(monkeypatch: pytest.MonkeyPatch) -> FakeBoundary:
    fake = FakeBoundary({case_to_record(c["invoice_data"])["Id"]: case_to_record(c["invoice_data"]) for c in CASES})
    monkeypatch.setattr(main, "read_invoice_record", fake.read_invoice_record)
    monkeypatch.setattr(main, "write_agent_outputs", fake.write_agent_outputs)
    monkeypatch.setattr(main, "generate_narrative", fake.generate_narrative)
    monkeypatch.setenv("AP_INVOICE_ENTITY_NAME", "AP_Invoice_Reference")
    return fake


@pytest.mark.parametrize("case", CASES, ids=[c["expected"]["invoice_reference"] for c in CASES])
async def test_graph_writes_expected_states_back_to_the_same_record(case, boundary: FakeBoundary):
    record = case_to_record(case["invoice_data"])
    expected = case["expected"]

    output = await main.graph.ainvoke({"recordId": record["Id"]})

    # Output contract (what the eval set / Lab 6 see)
    assert output["record_id"] == record["Id"]
    assert output["invoice_reference"] == expected["invoice_reference"]
    assert output["approval_evidence_state"] == expected["approval_evidence_state"]
    assert output["missing_approval_fields"] == expected["missing_approval_fields"]
    assert output["recommendation"] == expected["recommendation"]
    assert output["invoice_lifecycle_state"] == expected["invoice_lifecycle_state"]
    assert output["agent_processed_at"].endswith("Z")

    # Exactly one read and one write, to the same record, on the configured entity
    assert boundary.reads == [("AP_Invoice_Reference", record["Id"])]
    assert len(boundary.writes) == 1
    entity_name, record_id, fields = boundary.writes[0]
    assert (entity_name, record_id) == ("AP_Invoice_Reference", record["Id"])

    # Exactly the six agent output fields, nothing else (no Status, no second identifier)
    assert set(fields) == set(AGENT_OUTPUT_FIELDS)
    assert fields["ApprovalEvidenceState"] == expected["approval_evidence_state"]
    assert fields["MissingApprovalFields"] == ", ".join(expected["missing_approval_fields"])
    assert fields["AgentRecommendation"] == expected["recommendation"]
    assert fields["InvoiceLifecycleState"] == expected["invoice_lifecycle_state"]
    assert fields["AgentProcessedAt"] == output["agent_processed_at"]

    # The package is valid JSON and carries the decision + narrative only for gate 4
    package = json.loads(fields["ApprovalPackageJson"])
    assert package["recordId"] == record["Id"]
    assert package["decision"]["agentRecommendation"] == expected["recommendation"]
    assert package["decision"]["missingApprovalFields"] == expected["missing_approval_fields"]
    is_ready = expected["recommendation"] == "READY_FOR_APPROVAL"
    assert output["narrative_generated"] is is_ready
    assert (package["narrative"] is not None) is is_ready
    assert len(boundary.narratives) == (1 if is_ready else 0)


async def test_llm_runs_only_after_all_gates_and_only_for_gate4(boundary: FakeBoundary):
    ready = case_to_record(CASES[0]["invoice_data"])  # AP-TRAIN-1001
    await main.graph.ainvoke({"recordId": ready["Id"]})
    assert boundary.call_order == ["read", "llm", "write"]

    boundary.call_order.clear()
    held = case_to_record(CASES[3]["invoice_data"])  # AP-TRAIN-1004 (PO mismatch)
    await main.graph.ainvoke({"recordId": held["Id"]})
    assert boundary.call_order == ["read", "write"]


async def test_narrative_never_sees_ids_or_tax_ids(boundary: FakeBoundary):
    ready = case_to_record(CASES[0]["invoice_data"])
    ready["VendorName"] = "Northwind Office Supplies Inc."
    ready["VendorTaxId"] = "00-0000000"
    boundary.records[ready["Id"]] = ready
    await main.graph.ainvoke({"recordId": ready["Id"]})
    facts = boundary.narratives[0]
    assert "Id" not in facts and "VendorTaxId" not in facts
    assert facts["VendorName"] == ready["VendorName"]


async def test_entity_name_override_from_input(boundary: FakeBoundary):
    record = case_to_record(CASES[2]["invoice_data"])
    await main.graph.ainvoke({"recordId": record["Id"], "entityName": "AP_Invoice_Other"})
    assert boundary.reads == [("AP_Invoice_Other", record["Id"])]
    assert boundary.writes[0][0] == "AP_Invoice_Other"


def test_input_and_output_schemas_match_the_lab_contract():
    input_fields = set(main.GraphInput.model_fields)
    assert "recordId" in input_fields
    assert main.GraphInput.model_fields["recordId"].is_required()
    assert set(main.GraphOutput.model_fields) >= {
        "record_id",
        "approval_evidence_state",
        "missing_approval_fields",
        "recommendation",
        "invoice_lifecycle_state",
    }


def test_agent_output_fields_are_exactly_the_six_documented_fields():
    assert set(AGENT_OUTPUT_FIELDS) == {
        "ApprovalEvidenceState",
        "MissingApprovalFields",
        "AgentRecommendation",
        "ApprovalPackageJson",
        "AgentProcessedAt",
        "InvoiceLifecycleState",
    }
    assert "Status" not in AGENT_OUTPUT_FIELDS
