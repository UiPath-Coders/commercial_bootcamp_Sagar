"""Generate evaluations/eval-sets/smoke-test.json from the Lab 5 dataset.

The dataset template (lab-assets/vendor-invoice/evaluations/eval-sets/smoke-test.template.json)
assumes an ``invoice_data`` input. This agent takes ``recordId`` and reads the record itself, so
each case here:

* passes ``{"recordId": "<AP-TRAIN-xxxx>"}`` as input,
* mocks ``read_invoice_record`` (mockito) to return the matching seed row from
  ``seeds/data-fabric-input.csv`` (the same data participants import as evaluation records),
* mocks ``write_agent_outputs`` so nothing is written to a tenant,
* mocks ``generate_narrative`` so no LLM call is made,
* keeps the expected outputs from decision-cases.json verbatim (JsonSimilarityEvaluator).

Run:  .venv/bin/python scripts/build_smoke_test.py
Then: uip codedagent eval agent evaluations/eval-sets/smoke-test.json --no-report

To evaluate against a live tenant instead, delete the ``mockingStrategy`` blocks and replace each
``recordId`` with the real Data Fabric Id captured after importing the seed CSV.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LAB_ASSETS = PROJECT.parents[1] / "lab-assets" / "vendor-invoice"
CASES = LAB_ASSETS / "evaluations" / "decision-cases.json"
SEEDS = LAB_ASSETS / "seeds" / "data-fabric-input.csv"
OUT = PROJECT / "evaluations" / "eval-sets" / "smoke-test.json"

NAMES = {
    "AP-TRAIN-1001": "Complete evidence - ready for approval",
    "AP-TRAIN-1002": "Missing receipt reference - AP review required",
    "AP-TRAIN-1003": "Under threshold and matched - auto-approved",
    "AP-TRAIN-1004": "PO mismatch - hold",
    "AP-TRAIN-1005": "Missing GL account and approver - AP review required",
    "AP-TRAIN-1006": "Complete evidence - second ready-for-approval case",
}


def seed_records() -> dict[str, dict]:
    with SEEDS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    records = {}
    for row in rows:
        record = {k: (v if v != "" else None) for k, v in row.items()}
        record["Id"] = row["InvoiceReference"]
        records[row["InvoiceReference"]] = record
    return records


def mock_narrative(record: dict) -> dict:
    return {
        "summary": (
            f"Invoice {record['InvoiceNumber']} from {record['VendorName']} for {record['TotalAmount']} "
            f"{record['Currency']} is matched to {record['PONumber']}; evidence complete (mocked narrative)."
        ),
        "risk_flags": [],
        "confidence": "high",
        "source": "mock",
        "model": "mock",
        "reason": None,
    }


def build() -> dict:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    seeds = seed_records()
    evaluations = []
    for index, case in enumerate(cases, start=1):
        ref = case["expected"]["invoice_reference"]
        record = seeds[ref]
        mocks = [
            {"function": "read_invoice_record", "then": [{"type": "return", "value": record}]},
            {"function": "write_agent_outputs", "then": [{"type": "return", "value": {**record, "Mocked": True}}]},
        ]
        if case["expected"]["recommendation"] == "READY_FOR_APPROVAL":
            mocks.append({"function": "generate_narrative", "then": [{"type": "return", "value": mock_narrative(record)}]})
        evaluations.append(
            {
                "id": f"test-{index}-{ref.lower()}",
                "name": NAMES[ref],
                "inputs": {"recordId": ref},
                "evaluationCriterias": {"JsonSimilarityEvaluator": {"expectedOutput": case["expected"]}},
                "mockingStrategy": {"type": "mockito", "config": mocks},
            }
        )
    return {
        "version": "1.0",
        "id": "vendor-invoice-approval-smoke",
        "name": "Vendor Invoice Approval Smoke Tests",
        "description": (
            "Deterministic gate paths for the six synthetic AP-TRAIN invoices. Data Fabric and the LLM are "
            "mocked (mockito) so the set runs offline; expected outputs come from decision-cases.json."
        ),
        "evaluatorRefs": ["JsonSimilarityEvaluator"],
        "evaluations": evaluations,
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(PROJECT)} with {len(build()['evaluations'])} cases")
