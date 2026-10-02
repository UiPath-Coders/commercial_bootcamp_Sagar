# Day 1 to Day 2 Handoff Contract

Day 2 continues the resources and records created on Day 1. It must not create a parallel invoice data
model. The canonical process is defined in the bootcamp app (`docs/commercial-process.md`).

## Verified Day 1 outputs

| Lab | Verified output | Day 2 dependency |
| --- | --- | --- |
| Environment Setup | Coding-agent desktop app with the `uipath` plugin, UiPath CLI, Git/GitHub authentication, and a private full copy at `UiPath-Coders/commercial_bootcamp_<name>` | Lab 5 begins in a new session inside `commercial_bootcamp_<name>/lab5-coded-agent`; the golden `commercial_bootcamp_lab_assets` clone remains read-only reference material. |
| Lab 1 | Live IXP project `Vendor Invoice <user_name>` extracting Vendor Name, Vendor Tax ID, Invoice Number, Invoice Date, PO Number, Total Amount, Currency, Due Date | Remains the extraction source referenced by the Day 1 solution and documented in Lab 7. |
| Lab 2 | Folder `APAutomation_<user_name>`, bucket `InvoiceInbox_<user_name>`, queue `InvoiceQueue_<user_name>`, tenant-scoped entity `AP_Invoice_<user_name>` | Labs 5–10 reuse these resources. Data Fabric operations remain tenant-scoped. |
| Lab 2 | The entity contains `ProcessedTimestamp`, the eight IXP fields, `POMatched`, `ApprovalNeeded`, `PostedToERP` | Lab 5 adds only the missing approval-input, agent-output, and reviewer-output fields. |
| Lab 2 | Each queue item `Reference` is the system-generated Data Fabric record `Id` | That `Id`, not the invoice number or the queue transaction ID, is the canonical invoice identifier. |
| Lab 3 | The `POMatch_<user_name>` Python function (`process_invoice_queue`) sets `POMatched` and `ApprovalNeeded` on the record referenced by each queue transaction and marks the transaction Successful | The selected Day 2 record must carry the real Lab 3 result before agent evaluation. |
| Lab 4 | `PostToERP_<user_name>` posts **ready-to-post** records (auto-approved on Day 1) in the mock AP portal and sets `PostedToERP = true` | Lab 4 reads Data Fabric, not the queue, so it never competes with Lab 3 for a transaction. Day 2 records that need approval are untouched by Lab 4 until they reach `APPROVED`. |

## Lab 5 normalization gate

1. Inspect the current Data Fabric records and the queue transaction history.
2. Select one existing Lab 2 record `Id` with `ApprovalNeeded = true` as `<CANONICAL_RECORD_ID>`.
3. Verify `POMatched` and `ApprovalNeeded` were produced by the Lab 3 orchestrator for that record.
4. If either value is missing, rerun Lab 3 against that record and update that same `Id` after explicit approval.
5. Never guess a result, create a replacement record, or use a different identifier later.

## Resource scope

| Resource | Scope rule |
| --- | --- |
| `AP_Invoice_<user_name>` | Tenant-scoped. Resolve its entity ID before use and omit the participant deployment folder from its operations. |
| `InvoiceQueue_<user_name>` | Folder-scoped to `APAutomation_<user_name>`. |
| Day 1 RPA / API processes | Folder-scoped to `APAutomation_<user_name>`. |
| Lab 5 coded agent | Deployed to `APAutomation_<user_name>` but reads the tenant-scoped entity. |
| Lab 6 coded app | Deployed to `APAutomation_<user_name>` but reads and writes the tenant-scoped entity. |

Data Fabric display labels and internal field names may differ. Every Day 2 implementation must discover
the live schema and map the exact case-sensitive internal names and types. The PascalCase names in the
labs (`POMatched`, `ApprovalNeeded`, …) are the intended system names, not permission to skip discovery.

## Day 2 startup gate

Ask Claude Code to confirm all of these before starting; it should report each as OK:

- `uip --version` returns 1.200 or later and `uip login status` shows `customersuccessamer` / `Training`.
- `git --version` and `gh auth status` succeed.
- The `uipath` plugin is installed (`/uipath:uipath-agents`, `/uipath:uipath-data-fabric`, `/uipath:uipath-coded-apps`, `/uipath:uipath-planner`, `/uipath:uipath-governance`, `/uipath:uipath-admin` autocomplete).

## Canonical handoff card

Record these values at the beginning of Lab 5 and carry them through Lab 10:

| Value | Required evidence |
| --- | --- |
| `<FOLDER_NAME>` and `<FOLDER_KEY>` | Resolved `APAutomation_<user_name>` folder. |
| `<QUEUE_NAME>` | `InvoiceQueue_<user_name>`. |
| `<ENTITY_NAME>`, `<ENTITY_ID>`, `<ENTITY_KEY>` | Live tenant-scoped entity discovery. `<ENTITY_KEY>` is the same value as `<ENTITY_ID>` (the SDK calls it entity_key). |
| `<CANONICAL_RECORD_ID>` | Existing Lab 2 Data Fabric record `Id`. |
| Queue correlation | A queue `Reference` equal to `<CANONICAL_RECORD_ID>`. |
| Day 1 state | Exact `POMatched` and `ApprovalNeeded` values plus evidence of the originating Lab 3 run. |
| Lab 5 state | Agent name, deployment reference, recommendation, and lifecycle state for the same record. |
| Lab 6 state | App name, deployment URL, and the reviewer decision (`APPROVED` / `REJECTED`, `ReviewedBy`, `ReviewedAt`) written to the same record. |

Do not put tokens, client secrets, vendor tax IDs, bank details, or raw participant identity values in the
handoff card or in GitHub.

## Day 2 completion story

| Lab | Completion contribution |
| --- | --- |
| 5 | Normalizes one Day 1 record, extends the same entity once, and writes a deterministic recommendation to that same `Id`. |
| 6 | Reads the same entity in a deployed reviewer app, and a human approves or rejects the same record. |
| 7 | Documents current state separately from target state and produces an implementation-grade design and task graph. |
| 8 | Inspects the deployment read-only with sensitive values redacted. |
| 9 | Designs governance and proves effective access without changing shared-tenant access. |
| 10 | Assembles every component into one solution and runs the process end-to-end, including the human approval. |
