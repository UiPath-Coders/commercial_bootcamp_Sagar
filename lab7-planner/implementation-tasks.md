# Invoice Approval Solution — Implementation Tasks

**Source SDD:** `invoice-approval-solution-sdd.md` (root) + children `invoice-approval-process-sdd.md`, `invoice-intake-rpa-sdd.md`, `invoice-extraction-agent-sdd.md`, `invoice-approval-agent-sdd.md`, `ap-approval-review-sdd.md`, `post-to-erp-sdd.md`
**SDD scope:** solution (Solution ID `invoice-approval`; root + 6 children verified `Status: ready`, same Solution ID)
**Execution autonomy:** autonomous
**Delivery model:** cloud (tenant *Training*, `staging.uipath.com`, folder `Agentic Bootcamp/APAutomation_Sagar`)
**Generation date:** 2026-10-08
**App type:** web (Globex AP portal) · **UI targeting:** N/A — `PostToERP_Sagar` already built; UI targeting questions skipped at the user's request · **App state:** N/A

> Tasks below are derived from the SDDs. The SDDs remain the architectural source of truth.
> **Execution gate:** this file was written in Lab 7 Step 6 for review only. **No task has been started.** Execution begins only when the user explicitly asks for it in a later turn.
> **Coded app boundary:** `ap-approval-review-sagar` (T13–T15) is built, packed, published and deployed by `uipath-coded-apps` on its own. It is **not** added to the `.uipx` solution in T22.

## How to read a task

Every task names: **Changes** (the artifact or resource it touches), the owning **skill** (in the heading), **Blocked by** (dependencies), and **Acceptance evidence** (what proves it is done). "Reuse-and-verify" tasks change nothing unless verification fails.

## Dependency order (summary)

| # | Skill | Task | Changes | Blocked by |
|---|---|---|---|---|
| T1 | uipath-platform | Add `RejectionReason` field | Data Fabric entity `AP_Invoice_Sagar` | none |
| T2 | uipath-platform | Verify shared runtime and resources | none (read-only) | none |
| T3 | uipath-platform | Create portal credential asset | Orchestrator asset `AP_Portal_Credential` | none |
| T4 | uipath-ixp | Validate IXP model | none (read-only) | none |
| T5 | uipath-agents | Reuse-and-verify extraction agent | `Invoice_Extraction_Agent_Sagar` (verify) | T4 |
| T6 | uipath-agents | Testing — extraction agent | none | T5 |
| T7 | uipath-rpa | Reuse-and-verify intake robot | `Invoice_Intake_RPA_Sagar` (verify) | T2, T6 |
| T8 | uipath-rpa | Testing — intake robot | test records | T7 |
| T9 | uipath-functions | Add rejection-reason passthrough | `POMatch_Sagar` `get_invoice_status` + 4 processes | T1, T2 |
| T10 | uipath-functions | Testing — POMatch functions | none | T9 |
| T11 | uipath-agents | Reuse-and-verify approval agent | `Invoice_Approval_Agent_Sagar` (verify) | T1 |
| T12 | uipath-agents | Testing — approval agent | eval records | T11 |
| T13 | uipath-coded-apps | Rejection reason in review app | `lab6-coded-app/ap-approval-review-Sagar` source | T1 |
| T14 | uipath-coded-apps | Testing — review app | one test record decision | T13 |
| T15 | uipath-coded-apps | Deploy review app v1.0.1 (outside `.uipx`) | coded-app package + deployment | T14 |
| T16 | uipath-rpa | Portal sign-in from credential asset | `lab4-rpa/PostToERP_Sagar` workflows | T3 |
| T17 | uipath-rpa | Testing — posting robot | test record postings | T16 |
| T18 | uipath-platform | Publish PostToERP_Sagar new version | package + process `PostToERP_Sagar` | T17 |
| T19 | uipath-maestro-bpmn | Author orchestration process | `lab10-maestro-bpmn/InvoiceApprovalSolution_Sagar/...` | T8, T10, T12, T18 |
| T20 | uipath-maestro-bpmn | Testing — orchestration (debug) | debug solutions (listed) | T19 |
| T21 | uipath-maestro-bpmn | Pre-pack hygiene and pack check | `resources/`, pack output | T20 |
| T22 | uipath-solution | Publish and deploy `.uipx` | solution package + new child folder | T21 |
| T23 | uipath-maestro-bpmn | End-to-end verification, all routes | instances on reserved test files | T15, T22 |
| T24 | uipath-platform | Post-deploy verification and cleanup list | none (read-only report) | T23 |

24 tasks · skills: uipath-platform (5), uipath-ixp (1), uipath-agents (4), uipath-rpa (4), uipath-functions (2), uipath-coded-apps (3), uipath-maestro-bpmn (4), uipath-solution (1).

## Stop conditions

Execution (when later authorized) must stop and ask the user only for these:

- `uip login status` shows another tenant and `uip login tenant set Training` fails, or a 401 persists after one `uip login refresh --login-validity 60`.
- `ERP_PO_LOOKUP_URL` token `exp` is in the past and no fresh signed URL has been provided by the user.
- Any step would need to create a machine, machine template, robot account or role.
- A reviewer decision is needed in the app (T14, T23): stop and name the exact InvoiceNumber and VendorName to decide.
- A record would need clearing or deleting to rerun a test; ask before changing it.
- `uip solution deploy run` fails twice for a reason other than a single `HTTP 500 Execution Timeout` (rerun once).
- An old solution deployment would need uninstalling: never uninstall; report it for the facilitator.

---

## Task T1 — uipath-platform — Add `RejectionReason` field to the invoice entity

**Identity:** `platform:AP_Invoice_Sagar:entity-field:RejectionReason`
**Status:** [ ] pending
**Blocked by:** none
**Changes:** Data Fabric entity `AP_Invoice_Sagar` (tenant-scoped) — one new user field.
**Acceptance evidence:** `uip df entities get` lists 28 user fields including `RejectionReason` (text, ≤ 500 chars); existing 27 fields unchanged; no record values printed.
**Skill prompt:**

> Load uipath-platform. Add the field `RejectionReason` (text, max 500 characters) to Data Fabric entity `AP_Invoice_Sagar` as specified in `invoice-approval-solution-sdd.md` §5 Shared Assets & Queues and `ap-approval-review-sdd.md` §6 API Integration. Extend the entity once with an add-fields update; do not pass a folder key to `uip df`; touch no other `AP_Invoice_*` entity. Assumption pending SME confirmation: PDD Q5 rejection reason — proceeding with default "new entity field RejectionReason, required on Reject". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-solution-sdd.md`. Do not infer or guess.

- [ ] Read the entity id for `AP_Invoice_Sagar` and confirm 27 user fields before the change
- [ ] Add `RejectionReason` (text, 500) in a single add-fields update
- [ ] **Validate:** entity shows 28 user fields; `RejectionReason` present with the right type and length

## Task T2 — uipath-platform — Verify shared runtime and resources

**Identity:** `platform:APAutomation_Sagar:verify-shared-resources`
**Status:** [ ] pending
**Blocked by:** none
**Changes:** nothing (read-only verification).
**Acceptance evidence:** a short table showing: folder `Agentic Bootcamp/APAutomation_Sagar` resolved; Serverless runtime Total 1 (inherited); robot inherited; bucket `InvoiceInbox_Sagar` and queue `InvoiceQueue_Sagar` present; `ERP_PO_LOOKUP_URL` token `exp` in the future (only `exp` decoded, URL never printed).
**Skill prompt:**

> Load uipath-platform. Verify, read-only, the shared runtime and resources listed in `invoice-approval-solution-sdd.md` §5 Shared Assets & Queues: the participant folder, the inherited Default Serverless machine and robot, bucket `InvoiceInbox_Sagar`, queue `InvoiceQueue_Sagar`, and that the signed ERP URL used by the POMatch processes has not expired (decode only the token `exp`; never print the URL or token, never run `jobs get` where output is visible). Create nothing. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-solution-sdd.md`. Do not infer or guess.

- [ ] Resolve the folder key for `Agentic Bootcamp/APAutomation_Sagar`
- [ ] Check folder runtimes and inherited users
- [ ] Confirm bucket and queue exist
- [ ] Check the ERP URL token expiry without printing it
- [ ] **Validate:** every row of the evidence table is green, or the failing row is reported as a stop condition

## Task T3 — uipath-platform — Create the AP portal credential asset

**Identity:** `platform:APAutomation_Sagar:asset:AP_Portal_Credential`
**Status:** [ ] pending
**Blocked by:** none
**Changes:** new Orchestrator credential asset `AP_Portal_Credential` in `Agentic Bootcamp/APAutomation_Sagar`.
**Acceptance evidence:** asset listed in the folder with type Credential; value never echoed.
**Skill prompt:**

> Load uipath-platform. Create the credential asset `AP_Portal_Credential` in folder `Agentic Bootcamp/APAutomation_Sagar` as listed in `post-to-erp-sdd.md` §15 Credentials & Assets, holding the hosted AP portal sign-in. Never print or log the credential. Assumption pending SME confirmation: portal credential asset — proceeding with default `AP_Portal_Credential`, sign-in optional. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/post-to-erp-sdd.md`. Do not infer or guess.

- [ ] Create the credential asset in the participant folder
- [ ] **Validate:** asset appears in the folder's asset list with type Credential

## Task T4 — uipath-ixp — Validate the IXP model (live)

**Identity:** `ixp:Vendor Invoice Sagar:model-validation`
**Status:** [ ] pending
**Blocked by:** none
**Changes:** nothing unless metrics regress (then: label review and republish per the IXP skill).
**Acceptance evidence:** project `Vendor Invoice Sagar` model version tagged `live`; all 8 fields present in the taxonomy; per-field F1 recorded (baseline 1.0 on 5 validated documents).
**Skill prompt:**

> Load uipath-ixp. Validate the IXP project `Vendor Invoice Sagar` as described in `invoice-extraction-agent-sdd.md` §8 IXP / Document Understanding Models and §5 Evaluation Criteria: confirm the `live` tag, the eight-field taxonomy and the per-field metrics. Report Vendor Tax ID only as match/miss. Assumption pending SME confirmation: accuracy evidence — proceeding with default "F1 on the 5 validated documents; held-out set before production". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-extraction-agent-sdd.md`. Do not infer or guess.

- [ ] List model versions and tags
- [ ] Read project metrics per field
- [ ] **Validate:** `live` tag present; 8 of 8 fields at the recorded F1 baseline

## Task T5 — uipath-agents — Reuse-and-verify the extraction agent

**Identity:** `agents:Invoice_Extraction_Agent_Sagar:verify`
**Status:** [ ] pending
**Blocked by:** T4
**Changes:** `lab2-rpa/Invoice_Extraction_Agent_Sagar` — none expected; only if the IXP resource binding does not match the SDD.
**Acceptance evidence:** deployed process in `Agentic Bootcamp/APAutomation_Sagar/Invoice_Extraction_Agent_Sagar` at v1.0.0; IXP resource names project title `Vendor Invoice Sagar`, version tag `live`, `guardrail.policies []`; output schema has the 8 fields.
**Skill prompt:**

> Load uipath-agents. Verify the low-code agent `Invoice_Extraction_Agent_Sagar` against `invoice-extraction-agent-sdd.md` §3 Tools, §6 Orchestrator Bindings and §9 Project Structure. Change nothing if it matches; if the IXP resource binding differs, correct only that binding. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-extraction-agent-sdd.md`. Do not infer or guess.

- [ ] Compare `agent.json` input/output schema with §3 Agent Configuration
- [ ] Compare `resources/VendorInvoiceIXP/resource.json` with §6
- [ ] Confirm the deployed process and folder
- [ ] **Validate:** agent project validates; deployed version matches the source

## Task T6 — uipath-agents — Testing (MANDATORY) — extraction agent

**Identity:** `agents:Invoice_Extraction_Agent_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T5
**Changes:** none (evaluation runs only).
**Acceptance evidence:** evaluation results for T-01 to T-03 in `invoice-extraction-agent-sdd.md` §10; 8 of 8 keys on every run; no tax IDs or amounts in logs.
**Skill prompt:**

> Load uipath-agents and run its testing workflow end-to-end for `Invoice_Extraction_Agent_Sagar`. Always thorough: happy path + edge cases + error scenarios, using the evaluation dataset in `invoice-extraction-agent-sdd.md` §10 Testing Strategy. See that skill's testing references for commands, test-case authoring, and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-extraction-agent-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-agents' testing reference
- [ ] **Validate:** all tests pass; record results (Vendor Tax ID as match/miss only)

## Task T7 — uipath-rpa — Reuse-and-verify the intake robot

**Identity:** `rpa:Invoice_Intake_RPA_Sagar:verify`
**Status:** [ ] pending
**Blocked by:** T2, T6
**Changes:** `lab2-rpa/Invoice_Intake_RPA_Sagar` — none expected.
**Acceptance evidence:** `Main.xaml` / `ProcessInvoiceFile.xaml` arguments match `invoice-intake-rpa-sdd.md` §11 Workflow Inventory; BR-02/BR-03 validation and BR-04 duplicate lookup present; `uip rpa build` succeeds; deployed process at v1.0.2.
**Skill prompt:**

> Load uipath-rpa. Verify `Invoice_Intake_RPA_Sagar` against `invoice-intake-rpa-sdd.md` §4 Business Rules, §5 Data Definitions and §11 Project Structure, including the `CreateQueueItem = false` path used by the orchestration. Change nothing if it matches. Assumption pending SME confirmation: duplicate key — proceeding with default "Invoice Number only". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-intake-rpa-sdd.md`. Do not infer or guess.

- [ ] Compare workflow arguments with §11 Workflow Inventory
- [ ] Confirm BR-02, BR-03, BR-04 and BR-10 logic is present
- [ ] **Validate:** `uip rpa build` succeeds

## Task T8 — uipath-rpa — Testing (MANDATORY) — intake robot

**Identity:** `rpa:Invoice_Intake_RPA_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T7
**Changes:** creates test records for valid test files only (synthetic).
**Acceptance evidence:** results for HP-1, HP-2, B1a, B1b, B2, B3 and E1/E2/E4 in `invoice-intake-rpa-sdd.md` §17; an invalid file creates no record; a repeat file returns `WasDuplicate = true` with the same Id.
**Skill prompt:**

> Load uipath-rpa and run its testing workflow end-to-end for `Invoice_Intake_RPA_Sagar`. Always thorough: happy path + edge cases + error scenarios, per `invoice-intake-rpa-sdd.md` §17 Testing Strategy, running serverless jobs in `Agentic Bootcamp/APAutomation_Sagar`. Do not use the files reserved for the Lab 10 reviewer path or Challenge 011. See that skill's testing references for commands, test-case authoring, and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-intake-rpa-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-rpa's testing reference
- [ ] **Validate:** all tests pass; record results without amounts or tax IDs

## Task T9 — uipath-functions — Add rejection-reason passthrough to `get_invoice_status`

**Identity:** `functions:POMatch_Sagar:get_invoice_status:rejection_reason`
**Status:** [ ] pending
**Blocked by:** T1, T2
**Changes:** `lab3-api/POMatch_Sagar/main.py` (`InvoiceStatusOutput` gains `rejection_reason`); new package version; processes `POMatch_Sagar_po_lookup`, `_process_invoice`, `_process_invoice_queue`, `_get_invoice_status` moved to it and each re-bound to its own entry point; `ERP_PO_LOOKUP_URL` kept on the process env vars.
**Acceptance evidence:** `uip or packages entry-points POMatch_Sagar:<new version>` lists 4 entry points; a `get_invoice_status` job on a REJECTED record returns `rejection_reason`; a `process_invoice` job started without `--environment-variables` succeeds (proves the process env var).
**Skill prompt:**

> Load uipath-functions. Extend `POMatch_Sagar.get_invoice_status` so its output also returns the record's `RejectionReason` as `rejection_reason`, as listed in `invoice-approval-process-sdd.md` §9 Integrated Components → Coded Functions. Keep BR-1/BR-2 logic (2% two-sided tolerance, > 10,000 USD threshold), the safe boolean defaults and the httpx WARNING log level unchanged. Publish a new version and keep every process bound to its own entry point. Never print the signed ERP URL or token. Assumption pending SME confirmation: tolerance direction — proceeding with default "two-sided, as built". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Add `rejection_reason` to the status output model and read it case-insensitively
- [ ] Pack and publish the new version
- [ ] Move all four processes to the new version and re-bind each entry point
- [ ] **Validate:** entry points listed for the new version; local `uip function run get_invoice_status` returns the new field

## Task T10 — uipath-functions — Testing (MANDATORY) — POMatch functions

**Identity:** `functions:POMatch_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T9
**Changes:** none.
**Acceptance evidence:** `test_rules.py`, `test_po_lookup_live.py`, `test_po_lookup_errors.py` pass; serverless jobs for `process_invoice` (matched / not found / inactive / outside tolerance) and `get_invoice_status` succeed.
**Skill prompt:**

> Load uipath-functions and run its testing workflow end-to-end for `POMatch_Sagar`. Always thorough: happy path + edge cases + error scenarios, covering every match reason and error type in `invoice-approval-process-sdd.md` §9 Coded Functions and the rule definitions in `invoice-approval-pdd.md` §8. See that skill's testing references for commands and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-functions' testing reference
- [ ] **Validate:** all tests pass; record results without amounts

## Task T11 — uipath-agents — Reuse-and-verify the approval agent

**Identity:** `agents:Invoice_Approval_Agent_Sagar:verify`
**Status:** [ ] pending
**Blocked by:** T1
**Changes:** `lab5-coded-agent/agent/Invoice_Approval_Agent_Sagar` — none expected; confirm `RejectionReason` is never written by the agent and the retry guard never downgrades APPROVED / REJECTED / POSTED.
**Acceptance evidence:** gates 1–4 and the retry guard match `invoice-approval-agent-sdd.md` §3; VendorTaxId absent from graph state; deployed process `Invoice_Approval_Agent_Sagar` v0.0.1 (or a new version if a fix was needed).
**Skill prompt:**

> Load uipath-agents. Verify the coded LangGraph agent `Invoice_Approval_Agent_Sagar` against `invoice-approval-agent-sdd.md` §3 Tools (gates and retry guard), §4 Memory and §9 Project Structure, and confirm it leaves the new `RejectionReason` field untouched. Change only what deviates from the SDD. Assumptions pending SME confirmation: required inputs — proceeding with default "4 of 7 required"; PDD Q1 — proceeding with default "HOLD_PO_MISMATCH, no package"; LLM model — proceeding with default `gpt-4o-2024-11-20`. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-agent-sdd.md`. Do not infer or guess.

- [ ] Compare `approval_gates.py` with the §3 gate table and retry guard
- [ ] Confirm graph state never holds VendorTaxId
- [ ] **Validate:** agent unit tests pass; project packs without error

## Task T12 — uipath-agents — Testing (MANDATORY) — approval agent

**Identity:** `agents:Invoice_Approval_Agent_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T11
**Changes:** evaluation writes to the eval records (as designed).
**Acceptance evidence:** eval T-01 to T-07 in `invoice-approval-agent-sdd.md` §10 pass; trace spans show no LLM call on gates 1–3 and no second LLM call on a prepared gate-4 record.
**Skill prompt:**

> Load uipath-agents and run its testing workflow end-to-end for `Invoice_Approval_Agent_Sagar`. Always thorough: happy path + edge cases + error scenarios, per `invoice-approval-agent-sdd.md` §5 Evaluation Criteria and §10 Testing Strategy. Ask the user before clearing agent fields on any record. See that skill's testing references for commands and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-agent-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-agents' testing reference
- [ ] **Validate:** all tests pass; record results (show record Id only, never update responses)

## Task T13 — uipath-coded-apps — Capture the rejection reason in the review app

**Identity:** `coded-apps:ap-approval-review-sagar:rejection-reason`
**Status:** [ ] pending
**Blocked by:** T1
**Changes:** `lab6-coded-app/ap-approval-review-Sagar/src` (decision panel and decision patch); version bump to 1.0.1. Not part of the `.uipx` solution.
**Acceptance evidence:** Reject requires a 1–500 character reason and writes `RejectionReason`, `ReviewedBy`, `ReviewedAt`, `InvoiceLifecycleState = REJECTED` to exactly one record; `npm run build` succeeds.
**Skill prompt:**

> Load uipath-coded-apps. In `ap-approval-review-sagar`, add a required rejection-reason input to the decision panel and include `RejectionReason` in the Reject patch, per `ap-approval-review-sdd.md` §4 Components, §6 API Integration (decision patch) and §7 User Flows. Keep Approve/Reject enabled for READY_FOR_APPROVAL and NEEDS_AP_REVIEW with ApprovalNeeded true, keep the incomplete-evidence note, address the entity by name, and do not display VendorTaxId. This app is deployed on its own and is not part of the `.uipx` solution. Assumption pending SME confirmation: PDD Q2 — proceeding with default "both actions enabled on NEEDS_AP_REVIEW". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/ap-approval-review-sdd.md`. Do not infer or guess.

- [ ] Add the reason input and its validation to the decision panel
- [ ] Add `RejectionReason` to the Reject patch
- [ ] Bump the app version to 1.0.1
- [ ] **Validate:** `npm run build` succeeds with no type errors

## Task T14 — uipath-coded-apps — Testing (MANDATORY) — review app

**Identity:** `coded-apps:ap-approval-review-sagar:testing`
**Status:** [ ] pending
**Blocked by:** T13
**Changes:** one test record decided by the user (named by InvoiceNumber and VendorName before acting).
**Acceptance evidence:** T-01 to T-05 in `ap-approval-review-sdd.md` §11 pass; after a decision, no other record changed to APPROVED or REJECTED.
**Skill prompt:**

> Load uipath-coded-apps and run its testing workflow end-to-end for `ap-approval-review-sagar`. Always thorough: happy path + edge cases + error scenarios, per `ap-approval-review-sdd.md` §11 Testing Strategy. Before any decision, tell the user the exact InvoiceNumber and VendorName to act on; do not use the Lab 10 reviewer-path invoice. See that skill's testing references for commands and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/ap-approval-review-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-coded-apps' testing reference
- [ ] **Validate:** all tests pass; only the named record changed state

## Task T15 — uipath-coded-apps — Deploy the review app v1.0.1 (outside the `.uipx`)

**Identity:** `coded-apps:ap-approval-review-sagar:deploy`
**Status:** [ ] pending
**Blocked by:** T14
**Changes:** coded-app package `ap-approval-review-sagar` v1.0.1 published and deployed to folder `Agentic Bootcamp/APAutomation_Sagar`.
**Acceptance evidence:** `uip or packages list` shows `ap-approval-review-sagar:1.0.1`; the app URL returns HTTP 200; the deployed app shows the reason input on Reject.
**Skill prompt:**

> Load uipath-coded-apps and deploy `ap-approval-review-sagar` version 1.0.1 to folder `Agentic Bootcamp/APAutomation_Sagar` through the coded-app lifecycle (build, pack, publish, deploy), per `ap-approval-review-sdd.md` §10 Project Structure → Deployment Target. Do not add this app to any `.uipx` solution. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/ap-approval-review-sdd.md`. Do not infer or guess.

- [ ] Build, pack, publish and deploy version 1.0.1
- [ ] **Validate:** package listed at 1.0.1; app URL returns HTTP 200

## Task T16 — uipath-rpa — Read the portal sign-in from the credential asset

**Identity:** `rpa:PostToERP_Sagar:PostInvoiceInPortal.xaml:credential-asset`
**Status:** [ ] pending
**Blocked by:** T3
**Changes:** `lab4-rpa/PostToERP_Sagar/PostInvoiceInPortal.xaml` (optional sign-in reads `AP_Portal_Credential`); package version bump. Selectors and Object Repository unchanged.
**Acceptance evidence:** no plain-text portal password in the project; `grep -rl localhost` (excluding `.local`) is empty; `grep -c "role='AX"` prints 0; `uip rpa build` succeeds.
**Skill prompt:**

> Load uipath-rpa. In `PostToERP_Sagar`, make the optional portal sign-in read its username and password from credential asset `AP_Portal_Credential`, per `post-to-erp-sdd.md` §15 Credentials & Assets and §11 Workflow Inventory row 3. Keep the sign-in optional (Try/Catch, short timeout), keep every existing id-based selector and the Object Repository as they are, and keep the Main output names un-prefixed with no shadowing locals. UI targeting is already done; do not re-capture targets. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/post-to-erp-sdd.md`. Do not infer or guess.

- [ ] Replace the literal sign-in values with the credential asset
- [ ] Run the localhost and AX selector checks
- [ ] **Validate:** `uip rpa build` succeeds

## Task T17 — uipath-rpa — Testing (MANDATORY) — posting robot

**Identity:** `rpa:PostToERP_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T16
**Changes:** posts test records in the hosted portal (synthetic).
**Acceptance evidence:** HP-1 (auto-approved), HP-2 (approved), B1 (already posted), B2/B2b (held / rejected) in `post-to-erp-sdd.md` §17 pass on serverless jobs against the hosted portal; one posting per record.
**Skill prompt:**

> Load uipath-rpa and run its testing workflow end-to-end for `PostToERP_Sagar`. Always thorough: happy path + edge cases + error scenarios, per `post-to-erp-sdd.md` §17 Testing Strategy, using serverless jobs and the hosted portal URL only. See that skill's testing references for commands and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/post-to-erp-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-rpa's testing reference
- [ ] **Validate:** all tests pass; zero duplicate postings

## Task T18 — uipath-platform — Publish the new PostToERP_Sagar version

**Identity:** `platform:PostToERP_Sagar:process-version`
**Status:** [ ] pending
**Blocked by:** T17
**Changes:** package `PostToERP_Sagar` (new version) uploaded to the tenant feed; process `PostToERP_Sagar` moved to it.
**Acceptance evidence:** `uip or packages list` shows the new version; process runs a serverless smoke job successfully on the new version.
**Skill prompt:**

> Load uipath-platform. Upload the packed `PostToERP_Sagar` package from T16 to the tenant feed (without a folder key) and move process `PostToERP_Sagar` in `Agentic Bootcamp/APAutomation_Sagar` to that version, per `post-to-erp-sdd.md` §16 Delivery Quality Gates. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/post-to-erp-sdd.md`. Do not infer or guess.

- [ ] Upload the package and update the process version
- [ ] **Validate:** one serverless smoke job on an auto-approved record succeeds

## Task T19 — uipath-maestro-bpmn — Author the orchestration process

**Identity:** `maestro-bpmn:InvoiceApprovalProcess_Sagar:InvoiceApprovalProcess_Sagar.bpmn`
**Status:** [ ] pending
**Blocked by:** T8, T10, T12, T18
**Changes:** new project `commercial_bootcamp_Sagar/lab10-maestro-bpmn/InvoiceApprovalSolution_Sagar/InvoiceApprovalProcess_Sagar/` (`.bpmn`, project file, entry points, bindings) inside solution `InvoiceApprovalSolution_Sagar`.
**Acceptance evidence:** the process passes BPMN validation; it contains the 23 elements of §4, the gateways and flows of §5, the events of §6 (PT2M timer, 5 boundary errors, 5 ends) and the variables of §7; release keys are the real process Keys of the five Lab processes.
**Skill prompt:**

> Load uipath-maestro-bpmn. Author `InvoiceApprovalProcess_Sagar` exactly as specified in `invoice-approval-process-sdd.md` §4 Activities Inventory, §5 Gateways & Sequence Flows, §6 Events, §7 Data Objects & Variables, §9 Integrated Components and §10 Error Handling & Retry, inside solution `InvoiceApprovalSolution_Sagar` under `lab10-maestro-bpmn/`. Call the intake robot, POMatch functions, approval agent and posting robot as jobs with their real release keys; the reviewer decision is read by polling `get_invoice_status` every 2 minutes, at most 6 polls, then end Held. Follow the Lab 10 runtime rules in the project's CLAUDE.md. Assumptions pending SME confirmation: PDD Q1 — default "unmatched ends Held"; PDD Q8 — default "PT2M × 6 polls"; PDD Q7 — default "2 retries, 60 s"; trigger — default "manual / API start". Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Resolve the real process Keys of the five Lab processes in the participant folder
- [ ] Author the BPMN elements, flows, events and variables per §4–§7
- [ ] Write entry points (FileName input) and per-process bindings
- [ ] **Validate:** BPMN validation passes with no errors

## Task T20 — uipath-maestro-bpmn — Testing (MANDATORY) — orchestration

**Identity:** `maestro-bpmn:InvoiceApprovalProcess_Sagar:testing`
**Status:** [ ] pending
**Blocked by:** T19
**Changes:** debug runs (each leaves a Studio Web debug solution; ids are listed for cleanup).
**Acceptance evidence:** debug run on a file whose record is already POSTED ends `End_Paid` via `WasAlreadyPosted`; gateway branches of §13 Gateway / Branch Coverage exercised where possible without consuming reserved files; list of debug solution ids.
**Skill prompt:**

> Load uipath-maestro-bpmn and run its testing workflow end-to-end for `InvoiceApprovalProcess_Sagar`. Always thorough: happy path + gateway branches + boundary/timeout + error scenarios, per `invoice-approval-process-sdd.md` §13 Testing Strategy. Debug with a file whose record is already POSTED; never debug with the invoices reserved for Lab 10 Steps 4–5 or Challenge 011. See that skill's testing references for commands and best practices. Do not describe the testing procedure here — the specialist owns it. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Run testing workflow per uipath-maestro-bpmn's testing reference
- [ ] **Validate:** all tests pass; debug solution ids recorded for cleanup

## Task T21 — uipath-maestro-bpmn — Pre-pack hygiene and pack check

**Identity:** `maestro-bpmn:InvoiceApprovalSolution_Sagar:pre-pack-hygiene`
**Status:** [ ] pending
**Blocked by:** T20
**Changes:** solution `resources/` (environment variables cleared from refreshed resource files); pack output (git-ignored).
**Acceptance evidence:** grep of `resources/` finds no `access_token` and no populated `environmentVariables`; grep of the packed zip (including nested packages) finds no `access_token=`.
**Skill prompt:**

> Load uipath-maestro-bpmn. Refresh solution `InvoiceApprovalSolution_Sagar` resources, clear any process environment variables copied into resource files, pack it, and prove the pack contains no signed URL or token, per `invoice-approval-process-sdd.md` §12 Project Structure and the security row of its Non-Functional Requirements. Never print a token or URL. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Refresh resources and clear copied environment variables
- [ ] Pack the solution
- [ ] **Validate:** both greps return no matches

## Task T22 — uipath-solution — Publish and deploy the `.uipx` solution

**Identity:** `solution:InvoiceApprovalSolution_Sagar:publish-deploy`
**Status:** [ ] pending
**Blocked by:** T21
**Changes:** solution package `InvoiceApprovalSolution_Sagar` published; deploy configuration **links** the five Lab processes (`Invoice_Intake_RPA_Sagar`, `POMatch_Sagar_process_invoice`, `POMatch_Sagar_get_invoice_status`, `Invoice_Approval_Agent_Sagar`, `PostToERP_Sagar`) in `Agentic Bootcamp/APAutomation_Sagar`; one new child folder created by the deployment. The coded app is **not** in this solution.
**Acceptance evidence:** deployment status Successful; new child folder name reported; the deployed BPMN process is listed in it; linked processes are not duplicated as copies; any previous deployment folder reported for facilitator cleanup.
**Skill prompt:**

> Load uipath-solution. Publish `InvoiceApprovalSolution_Sagar`, generate its deploy configuration from the published package, link each of the five Lab processes to its existing process in `Agentic Bootcamp/APAutomation_Sagar` instead of installing copies, and deploy as a new child folder under that folder, per `invoice-approval-solution-sdd.md` §3 Project Inventory, §4 Cross-Project Data Flow and `invoice-approval-process-sdd.md` §12 Orchestrator Deployment Target. Do not include `ap-approval-review-sagar`. Never uninstall an existing deployment. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-solution-sdd.md`. Do not infer or guess.

- [ ] Publish the solution package
- [ ] Create the deploy configuration and link the five processes
- [ ] Deploy under `Agentic Bootcamp/APAutomation_Sagar` and read the deployment status
- [ ] **Validate:** status Successful; child folder name reported to the user

## Task T23 — uipath-maestro-bpmn — End-to-end verification, every route

**Identity:** `maestro-bpmn:InvoiceApprovalProcess_Sagar:e2e-verification`
**Status:** [ ] pending
**Blocked by:** T15, T22
**Changes:** process instances on unused synthetic invoice files; one approval and one rejection made by the user in the review app.
**Acceptance evidence:** instance element executions show `End_Paid` (approval route), `End_Paid` (auto-approved route), `End_Rejected` (reviewer reject with reason), `End_Invalid` (incomplete invoice) and `End_Held` (PO mismatch); records show the matching lifecycle states; no other record changed to APPROVED / REJECTED; PDD AC-1 to AC-13 traced.
**Skill prompt:**

> Load uipath-maestro-bpmn. Run the end-to-end orchestration test in `invoice-approval-process-sdd.md` §13 End-to-End Orchestration Test against the deployed solution: one instance per route (approval, auto-approved, reviewer reject, incomplete, PO mismatch), monitoring element executions and the poll count. For the reviewer routes, stop and tell the user the exact InvoiceNumber and VendorName to approve or reject in `ap-approval-review-sagar`. Trace the results to `invoice-approval-pdd.md` §15 Acceptance criteria. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-process-sdd.md`. Do not infer or guess.

- [ ] Start one instance per route with unused files
- [ ] Pause for the user's decisions in the review app
- [ ] Record each instance's end event and the record's final state
- [ ] **Validate:** all five routes end as designed; AC trace table complete

## Task T24 — uipath-platform — Post-deploy verification and cleanup inventory

**Identity:** `platform:APAutomation_Sagar:post-deploy-verification`
**Status:** [ ] pending
**Blocked by:** T23
**Changes:** nothing (read-only report).
**Acceptance evidence:** report listing: solution child folders (current and leftover), debug solution ids from T20, job outcomes per process in the folder and each solution sub-folder, record counts by lifecycle state (no amounts, no tax IDs), and open SME items still pending confirmation.
**Skill prompt:**

> Load uipath-platform. Produce a read-only post-deploy report for `Agentic Bootcamp/APAutomation_Sagar` per `invoice-approval-solution-sdd.md` §3 Project Inventory and §5 Shared Assets & Queues: folders created by deployments, debug solutions to clean up, job outcomes per process (check solution sub-folders separately), and invoice records by lifecycle state with confidential fields excluded. Change and delete nothing; leftover folders are reported for the facilitator. Use values, mappings, and structure exactly as documented in the SDD at `lab7-planner/invoice-approval-solution-sdd.md`. Do not infer or guess.

- [ ] List folders, debug solutions and job outcomes
- [ ] Count records by lifecycle state
- [ ] **Validate:** report complete; nothing changed in the tenant

---

## Open SME items carried as assumptions

These come from the SDDs' `Action Required — SME Review Items` tables. All are default-carried (Blocking = no) and must be confirmed before production sign-off:

1. PDD Q1 — approved but unmatched PO → default: ends Held, never posted (T11, T19)
2. PDD Q5 — rejection reason storage → default: new field `RejectionReason` (T1, T9, T13)
3. PDD Q8 — reviewer wait → default: PT2M × 6 polls, then Held (T19)
4. PDD Q4 — duplicate key → default: Invoice Number only (T7)
5. PDD Q3 — tolerance direction → default: two-sided (T9)
6. Required approval evidence → default: 4 of 7 inputs (T11)
7. PDD Q7 — ERP / portal retry → default: 2 retries, 60 s (T19)
8. PDD Q9 — vendor notification → default: out of scope
9. PDD Q10 — KPI baselines → default: measured after go-live
10. UAT / PROD environments → default: *Training* tenant only
11. Portal credential asset → default: `AP_Portal_Credential` (T3, T16)
12. Extraction accuracy evidence → default: 5 validated documents; held-out set before production (T4)
