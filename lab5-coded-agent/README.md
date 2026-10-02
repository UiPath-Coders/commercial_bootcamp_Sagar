# Lab 5 — Build Approval Package with a coded (LangGraph) agent

**What you build:** `Invoice_Approval_Agent_<user_name>`, a Python coded agent that prepares the approval
decision for a human. Given one invoice record Id it reads the record, runs **four deterministic gates in
order before any LLM reasoning**, asks the LLM for a short approval narrative only when all gates pass, and
writes six result fields back to the same record. It runs only for invoices that need approval.

**How you build it:** in the Claude Code desktop app, on your own copy of this repo, paste the prompts from the
Lab 5 page of the bootcamp site. Start with:

```text
Work inside commercial_bootcamp_<user_name>/lab5-coded-agent for the rest of this session. If that folder does not exist here, stop: tell me to finish Environment Setup and to open this session on my commercial-bootcamp folder, and do not create files anywhere else. Show me the folder layout and summarize day-1-to-day-2-handoff.md in five bullets.
```

## The four gates (memorise these)

| # | If… | ApprovalEvidenceState | AgentRecommendation | InvoiceLifecycleState |
|---|---|---|---|---|
| 1 | POMatched is false | NOT_EVALUATED | HOLD_PO_MISMATCH | HOLD_PO_MISMATCH |
| 2 | ApprovalNeeded is false | NOT_REQUIRED | AUTO_APPROVED | AUTO_APPROVED |
| 3 | GLAccount, CostCenter, Approver or ReceiptReference is empty | INCOMPLETE | NEEDS_AP_REVIEW (MissingApprovalFields lists them) | NEEDS_AP_REVIEW |
| 4 | everything present | COMPLETE | READY_FOR_APPROVAL + LLM narrative in ApprovalPackageJson | READY_FOR_APPROVAL |

The agent always writes ApprovalEvidenceState, MissingApprovalFields, AgentRecommendation, ApprovalPackageJson,
AgentProcessedAt and InvoiceLifecycleState on the **same** `AP_Invoice_<user_name>` record. No second entity,
no `Status` field.

## What is in this folder

| File / folder | What it is | Who uses it |
|---|---|---|
| `agent/` | Empty on purpose: Claude Code creates **your** agent project here. Its README says what to expect. | You. |
| `lab-assets/vendor-invoice/seeds/` | `data-fabric-input.csv`: six training records (AP-TRAIN-1001…1006) to import as evaluation records. `day2-approval-enrichment.csv`: the seven approval-input fields per record. | Claude Code, in the seed steps. |
| `lab-assets/vendor-invoice/evaluations/` | `decision-cases.json`: the acceptance test, one expected outcome per case. `evaluators/` and `eval-sets/`: UiPath evaluation definitions. | You and the reference tests. |
| `lab-assets/vendor-invoice/api/po-lookup-responses.json` | The ERP answers per PO (same fixture the mock ERP serves). | Context. |
| `day-1-to-day-2-handoff.md`, `canonical-handoff.template.md` | What Day 1 leaves behind and the sanitized handoff you fill in during the lab (copy the template to `canonical-handoff.md`). | You. |
| `reference/Invoice_Approval_Agent_Reference/` | **The complete answer.** A LangGraph agent scaffolded with `uip codedagent new`: `approval_gates.py` (pure gates), `data_fabric.py` (SDK read/write), `narrative.py` (LLM through the UiPath gateway), `main.py` (the graph). 69 pytest tests cover every decision case and seed row; the offline eval set scores 6/6; `uip codedagent review` gives it 100. | You, at the end of the lab, to run the reference gate tests against your own gate function. Facilitators, to grade. |

## Try the reference in two minutes

```bash
cd reference/Invoice_Approval_Agent_Reference
uv sync && .venv/bin/python -m pytest -q                   # 70 passed
AP_INVOICE_FIXTURE_FILE=../../lab-assets/vendor-invoice/seeds/data-fabric-input.csv \
AP_INVOICE_NARRATIVE_MODE=template \
uip codedagent run agent '{"recordId":"AP-TRAIN-1001"}'    # READY_FOR_APPROVAL, six fields written to fixture-output/
```

## How to know you are done

1. The gates fire in order and the LLM is only called in gate 4 (read your graph: no LLM node before the gates).
2. The canonical record shows COMPLETE, empty MissingApprovalFields, READY_FOR_APPROVAL twice, a fresh
   AgentProcessedAt and a package JSON with the narrative.
3. The six evaluation records produce the outcomes in `decision-cases.json`; the reference gate tests pass
   against your gate function.
4. The agent project and `canonical-handoff.md` are committed to your repository (last step of the lab).

## Common mistakes

- Letting the LLM decide. The gates are code; the LLM only writes the narrative after gate 4.
- Creating an `ApprovalStatus` entity or a `Status` field. The record is the single source of truth.
- Fabricating Data Fabric bindings. Entities are not a bindable resource; `bindings.json` stays empty.
- Passing the entity **name** to the SDK. `get_record` and `update_record` take the entity **Id**; resolve the
  name once with `retrieve_by_name`.
- Reading `POMatched` from `uip df` output. The CLI serializes acronyms as `PoMatched` / `PoNumber` and nests
  records under `.Data.Items`; a `null` under the schema spelling is not an empty field.
- Committing `__uipath/` (the LangGraph checkpoint database). It is gitignored; keep it that way.

## Runtime notes from the dry run

- `ApprovalPackageJson` is `MULTILINE_TEXT` (never MULTILINE_MAX).
- `uip codedagent run` and `uip codedagent eval` reuse the `uip login` session; no `.env` is needed.
- The live evaluation writes to the six training records, so AP-TRAIN-1003 is already prepared afterwards.
  Clear its six agent fields before the deploy idempotency test, or use an untouched record. Prove "no second
  LLM call on rerun" on a gate-4 record such as AP-TRAIN-1006.
- `data-fabric-input.csv` has an `InvoiceReference` column with no schema field. Map imported records by
  `InvoiceNumber`.
- The eval template's expected-output keys must use the camelCase contract (`recordId`, `invoiceLifecycleState`, …).
- Deploy with `uip codedagent deploy --tenant`, then `uip or processes create … --folder-key <APAutomation key>`.
  `deploy --folder` fails.
- `Governance policy fetch failed … 403 policy_service_forbidden` in job logs is expected. The agent still runs.
- The reference predates the Lab 5 contract (no retry guard, no `wasAlreadyPrepared` / `errorType` /
  `errorMessage`, snake_case outputs). See its README.

All data is synthetic.
