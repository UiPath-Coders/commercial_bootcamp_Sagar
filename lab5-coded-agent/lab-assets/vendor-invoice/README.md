# Vendor Invoice Approval — Lab Dataset

All records in this package are synthetic. They are not real vendors, tax IDs, purchase orders,
bank details, or amounts.

## Day 2 workspace location

The golden copy lives under `lab5-coded-agent/lab-assets/vendor-invoice/` in
`UiPath-Coders/commercial_bootcamp_lab_assets`. Participants work in
`commercial_bootcamp_<user_name>/lab5-coded-agent`, their private full copy. The agent is created under
`agent/`; `canonical-handoff.md` stays at the lab root. Do not open this nested dataset folder as the coding
agent workspace and do not initialize another Git repository inside it.

## What participants use

- `seeds/day2-approval-enrichment.csv` — the seven approval-input values that can be added to **one existing
  Day 1 record** (the canonical record) without changing its identity, extraction, or PO-match fields.
- `seeds/data-fabric-input.csv` — six complete synthetic records (`AP-TRAIN-1001` … `1006`) used only to seed
  participant-scoped Lab 5 evaluation records **after** the live schema has been extended.
- `evaluations/decision-cases.json` — the six deterministic gate cases and their expected outputs.
- `evaluations/eval-sets/smoke-test.template.json` — a UiPath coded-agent evaluation template for the same six cases.
- `evaluations/evaluators/json-similarity.json` — the evaluator the template references.
- `api/po-lookup-responses.json` — the deterministic responses the included **mock ERP PO-lookup API** returns
  for every PO in the Lab 1–2 invoice datasets and in the seeds.

## Suggested lab mapping

1. **Labs 1–4** create the tenant-scoped entity, its records, and the queue references from the shared Day 1 repos.
2. **Lab 5 handoff** — select one existing Day 1 record `Id` with `ApprovalNeeded = true` as the canonical record and
   verify its Lab 3 result (`POMatched`, `ApprovalNeeded`).
3. **Lab 5 enrichment** — after the approved schema extension, use one row from `seeds/day2-approval-enrichment.csv`
   to populate only the seven approval-input fields on the canonical record. Pick a complete row (1001 or 1006) if
   you want the agent to reach `READY_FOR_APPROVAL`; pick 1002 or 1005 to exercise `NEEDS_AP_REVIEW`.
4. **Lab 5 evaluation** — reconcile `seeds/data-fabric-input.csv` with the extended live schema and import it as
   separate evaluation records. Do not overwrite the canonical Day 1 record.
5. **Lab 5 evaluation** — run `evaluations/decision-cases.json` (or the smoke-test template) and compare.
6. **Lab 6** — the canonical record and the evaluation records form the reviewer worklist; approve the canonical record.
7. **Lab 10** — compare final test evidence with the decision matrix.

## Evaluation record seeding

Do not import `data-fabric-input.csv` during the Day 1 handoff or use it to replace Lab 2 records. It is a Lab 5
evaluation fixture. After the schema extension, resolve the tenant-scoped participant entity, inspect its exact
internal field names and types, reconcile the CSV headers, and import without a folder key:

```text
uip df records import <ENTITY_ID> --file seeds/data-fabric-input.csv --output json
```

Then query the evaluation records by `InvoiceReference` and capture each system-generated `Id`. `InvoiceReference`
is a training label; only the Data Fabric `Id` is the canonical identifier.

## Gate decision matrix

| Reference | POMatched | ApprovalNeeded | Missing inputs | Recommendation / lifecycle |
|---|---|---|---|---|
| AP-TRAIN-1001 | true | true | none | `READY_FOR_APPROVAL` |
| AP-TRAIN-1002 | true | true | ReceiptReference | `NEEDS_AP_REVIEW` |
| AP-TRAIN-1003 | true | false | n/a | `AUTO_APPROVED` |
| AP-TRAIN-1004 | false | true | n/a | `HOLD_PO_MISMATCH` |
| AP-TRAIN-1005 | true | true | GLAccount, Approver | `NEEDS_AP_REVIEW` |
| AP-TRAIN-1006 | true | true | none | `READY_FOR_APPROVAL` |

## Agent evaluation template

`smoke-test.template.json` is source data for the six decision cases. Before running it, ask `uipath-agents`
to adapt each case to the actual `entry-points.json` schema (the lab's agent input is `recordId`) and either
mock the Data Fabric record read for offline evaluation or substitute real imported record IDs. Preserve the
expected deterministic output fields.

## Safety

- Do not replace the synthetic values with real vendor or banking data.
- Keep the `AP-TRAIN-*` references when sharing results.
