# Canonical Day 2 Handoff

## Repository

- Lab 5 starter: `UiPath-Coders/commercial_bootcamp_lab_assets` → `lab5-coded-agent/`
- Participant: `Sagar`

## UiPath resources

| Value | Verified result |
| --- | --- |
| Folder name | `APAutomation_Sagar` (`Agentic Bootcamp/APAutomation_Sagar`) |
| Folder key | `13165bc3-5dea-4722-89d9-61d7835347cb` |
| Queue name | `InvoiceQueue_Sagar` |
| Entity name | `AP_Invoice_Sagar` (tenant-scoped) |
| Entity ID | `5c5aadee-d6bd-f111-a6a9-6045bddc9767` |
| Entity key | `5c5aadee-d6bd-f111-a6a9-6045bddc9767` (= Entity ID; the SDK calls it entity_key) |
| Canonical record ID | `268bc81c-dfbd-f111-a6a9-6045bddbb45c` (InvoiceNumber `CLL-2026-3391`, Contoso Logistics LLC) |

## Day 1 evidence

| Check | Status | Evidence reference |
| --- | --- | --- |
| Queue Reference equals canonical record ID | OK | `InvoiceQueue_Sagar` item `21507755`, Reference = canonical record ID, status Successful (2026-10-02 19:18:46Z) |
| POMatched verified from Lab 3 | OK (`true`) | Set by job `2cb9f4a4-2701-4699-8938-3e5afb9fe4e9` (`POMatch_Sagar_process_invoice_queue`, Successful, 2026-10-02 19:18:34–19:18:52Z), which processed item `21507755` |
| ApprovalNeeded verified from Lab 3 | OK (`true`) | Same job and queue item as above |

Record state at Lab 5 start: `InvoiceLifecycleState = EXTRACTED`, `PostedToERP` unset (false).

## Lab 5 evidence

| Value | Result |
| --- | --- |
| Agent project | `agent/Invoice_Approval_Agent_Sagar/` (LangGraph, entrypoint `agent`) |
| Agent name | `Invoice_Approval_Agent_Sagar` |
| Recommendation | `READY_FOR_APPROVAL` (canonical record; ApprovalEvidenceState `COMPLETE`, MissingApprovalFields empty, LLM narrative in ApprovalPackageJson) |
| Lifecycle state | `READY_FOR_APPROVAL` (canonical record, was `EXTRACTED`) |
| Deployment reference | Package `Invoice_Approval_Agent_Sagar` `0.0.1` on the tenant feed; process `Invoice_Approval_Agent_Sagar`, Key `2cb7c282-4fe3-4b25-b1aa-d29aa944fe66`, in `Agentic Bootcamp/APAutomation_Sagar` (Serverless) |

### Tested contract (from `uip or packages entry-points Invoice_Approval_Agent_Sagar:0.0.1`)

| Direction | Field | Type |
| --- | --- | --- |
| Input | `recordId` | string, required |
| Output | `recordId` | string, required (echoes the input) |
| Output | `approvalEvidenceState` | string: NOT_EVALUATED, NOT_REQUIRED, INCOMPLETE, COMPLETE |
| Output | `missingApprovalFields` | string[] |
| Output | `recommendation` | string: HOLD_PO_MISMATCH, AUTO_APPROVED, NEEDS_AP_REVIEW, READY_FOR_APPROVAL |
| Output | `invoiceLifecycleState` | string |
| Output | `wasAlreadyPrepared` | boolean (default false) |
| Output | `errorType`, `errorMessage` | string or null |

### Test evidence

| Test | Result |
| --- | --- |
| Local run on the canonical record | COMPLETE / READY_FOR_APPROVAL, narrative source `llm` |
| Smoke evaluation, 6 AP-TRAIN cases, 1 worker | 6/6 pass (JsonSimilarity 1.0 each), matches the README decision matrix |
| Deployed job, AP-TRAIN-1003 after clearing its agent fields | Job `587a5256-ffc8-4718-969d-821f40c63aab` Successful: NOT_REQUIRED / AUTO_APPROVED, `wasAlreadyPrepared` false |
| Repeat job, same AP-TRAIN-1003 record | Job `4b3864a6-44d3-454b-acb8-2022a11ded60` Successful: `wasAlreadyPrepared` true; package hash, AgentProcessedAt, lifecycle state and UpdateTime unchanged |
| Deployed job, AP-TRAIN-1006 (gate 4, already prepared) | Job `3ed69239-3932-4f81-9c0c-c1f4d9e5b07b` Successful: `wasAlreadyPrepared` true; record unchanged; trace `a33451d4-8077-4728-b5cc-cf693f68fe4a` has 6 spans (load_record, entity_retrieve_by_name, entity_get_record, route_after_load, finish) and no LLM span |

Python environment for local runs: `C:\Users\Sagar.Agrawal\.venvs\Invoice_Approval_Agent_Sagar` (outside OneDrive, because of the Windows path-length limit).

## Lab 6 evidence

| Value | Result |
| --- | --- |
| App name | `ap-approval-review-Sagar` |
| Deployment URL | `<SANITIZED_APP_URL>` |
| Reviewer decision | `<APPROVED or REJECTED>` by `<user_email>` at `<REVIEWED_AT>` |

Do not record tokens, secrets, vendor tax IDs, bank details, or invoice amounts.
