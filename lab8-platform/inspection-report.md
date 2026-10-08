# Lab 8: platform inspection report

Tenant: Training (staging). Inspected 2026-10-08 with read-only `uip or` commands. Nothing was created or changed.
No ids, keys, emails or credentials are recorded here.

## 1. Folder: APAutomation_Sagar

| Property | Value |
|---|---|
| Path | `Agentic Bootcamp/APAutomation_Sagar` |
| Type | Standard (not personal) |
| Parent | `Agentic Bootcamp` (Standard, top-level) |
| Provision type | Automatic |
| Permission model | FineGrained |
| Feed type | Processes (uses the folder hierarchy feed) |
| Sub-folders | 1: `Invoice_Extraction_Agent_Sagar` (Solution folder, created by the Lab 2 solution deploy) |

### Users (with inherited), counted by role

13 principals in total on APAutomation_Sagar: 11 directory users, 1 directory group, 1 robot account.

| Role set | Count | Assignment |
|---|---|---|
| Automation Developer + Folder Administrator | 10 users + 1 group | inherited from Agentic Bootcamp |
| Automation Developer + Automation Publisher + Folder Administrator | 1 user | inherited |
| Folder Administrator only | 1 user | inherited |
| Automation User (robot account "Agentic Labs Robot") | 1 robot | shown as direct on this folder; role listed twice (direct + inherited) |

The same 13 principals hold the same roles directly on Agentic Bootcamp. Folder Administrator for the participant
group on Agentic Bootcamp is a known, accepted grant (Lab 2 creates a sub-folder).

### Machines

| Folder | Direct machine assignments |
|---|---|
| APAutomation_Sagar | none (normal; machines are inherited from the parent) |
| Agentic Bootcamp | "Default Serverless" (machine template, Serverless scope), inherited by every sub-folder |

No machine has static unattended, headless, non-production or test slots; capacity comes from the runtime pools below.

### Runtimes (Total / Connected / Available)

| Runtime type | APAutomation_Sagar | Agentic Bootcamp |
|---|---|---|
| Serverless | 1 / 0 / 0 | 1 / 0 / 0 |
| Serverless Test Automation | 1 / 0 / 0 | 1 / 0 / 0 |
| Automation Cloud | 0 / 0 / 0 | 1 / 0 / 0 |
| All other types | 0 | 0 |

Connected/Available 0 is normal for serverless: robots start on demand per job.

### Robot and library associations

- Robot: "Agentic Labs Robot" (robot account, Automation User) runs jobs on the inherited Default Serverless machine.
- Processes bound in APAutomation_Sagar (7, all on their latest version): Invoice_Intake_RPA_Sagar,
  POMatch_Sagar_po_lookup, POMatch_Sagar_process_invoice, POMatch_Sagar_process_invoice_queue,
  POMatch_Sagar_get_invoice_status, PostToERP_Sagar, Invoice_Approval_Agent_Sagar.
- Process in the solution sub-folder: Invoice_Extraction_Agent_Sagar.
- Libraries: none published to the tenant library feed (libraries are tenant-scoped, not folder-scoped).

## 2. Storage bucket: InvoiceEvidence_Lab

Pre-check: before creation, APAutomation_Sagar held one bucket (InvoiceInbox_Sagar) and no InvoiceEvidence_Lab.

| Setting | Value |
|---|---|
| Name | InvoiceEvidence_Lab |
| Folder | `Agentic Bootcamp/APAutomation_Sagar` (in 1 folder, not shared to others) |
| Description | Lab 8: synthetic invoice and approval evidence documents (test data only) |
| Storage provider | Orchestrator built-in (no external provider, container, connection string or credential store) |
| Access options | None (default read/write; not read-only, no audit-read restriction) |
| Encrypted flag | false (built-in Orchestrator storage) |
| Tags | lab = lab8, data = synthetic |

Verification:
- `buckets get` returned the settings above.
- Test upload: `bucket-test-note.txt` (synthetic text, 132 bytes, text/plain) uploaded to `test/bucket-test-note.txt`.
  `bucket-files list` returned exactly that one file. Pre-signed download URLs were not printed or saved.

## 3. Data Fabric: AP_Invoice_Sagar

Only AP_Invoice_Sagar was read. Other participants' AP_Invoice_* entities were filtered out client-side and not
opened. All reads used `entities get` and `records query`; nothing was created, updated or deleted.

| Property | Value |
|---|---|
| Name | AP_Invoice_Sagar (type Entity) |
| Description | Lab 2 AP invoice records |
| Scope | Tenant (no folder; empty folder id) |
| Record count | 11 (`records query` TotalCount) |
| Fields | 33 = 27 user fields + 6 system fields |
| Row-level security / analytics | off / off |
| Encrypted fields | none flagged |

Records by InvoiceLifecycleState: EXTRACTED 3, READY_FOR_APPROVAL 2, NEEDS_AP_REVIEW 2, AUTO_APPROVED 1,
HOLD_PO_MISMATCH 1, APPROVED 1, POSTED 1.

### Fields and data types

| Field | Type | Notes |
|---|---|---|
| Id | UUID | system, primary key |
| CreateTime, UpdateTime | DATETIME_WITH_TZ | system |
| CreatedBy, UpdatedBy, RecordOwner | RELATIONSHIP (SystemUser) | system |
| ProcessedTimestamp | DATETIME_WITH_TZ | |
| VendorName | STRING (200) | |
| VendorTaxId | STRING (200) | sensitive; never selected |
| InvoiceNumber | STRING (200) | |
| InvoiceDate, DueDate | DATE | |
| PONumber | STRING (200) | `uip df` returns it as PoNumber |
| TotalAmount | DECIMAL (2 dp) | never selected or saved |
| Currency | STRING (200) | |
| POMatched, ApprovalNeeded, PostedToERP | BOOLEAN | unset PostedToERP = false |
| InvoiceLifecycleState | STRING (200) | |
| GLAccount, CostCenter, Approver, PaymentTerms | STRING (200) | |
| VendorRiskScore, ReceiptReference | STRING (200) | |
| InvoiceLineSummary | STRING (1000) | |
| ApprovalEvidenceState, AgentRecommendation | STRING (200) | Lab 5 |
| MissingApprovalFields | STRING (500) | Lab 5 |
| ApprovalPackageJson | MULTILINE_TEXT (10000) | Lab 5; never selected |
| AgentProcessedAt, ReviewedAt | DATETIME_WITH_TZ | Lab 5 |
| ReviewedBy | STRING (200) | |

### Sample records (5, sorted by InvoiceNumber)

Read with `selectedFields` limited to the columns below, so VendorTaxId, TotalAmount and ApprovalPackageJson never
left the server. Approver, ReviewedBy and InvoiceLineSummary were also left out. No bank details appear in these
fields (output was also scanned for IBAN/account-number patterns: none). Blank = unset.

| InvoiceNumber | Vendor | Invoice date | Due date | PO | Cur | Terms | PO matched | Approval needed | Posted | State | Evidence | Agent rec. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AF19427 | Ableton Fabrication, Inc. | 2026-03-09 | 2026-04-08 | PO-2026-0452 | USD | | true | false | false | EXTRACTED | | |
| BHC-4471 | Blue Harbor Catering Co. | 2026-03-11 | 2026-03-26 | PO-2026-0461 | USD | | false | true | false | EXTRACTED | | |
| CLL-2026-3391 | Contoso Logistics LLC | 2026-03-06 | 2026-04-20 | PO-2026-0447 | USD | Net 30 | true | true | false | APPROVED | COMPLETE | READY_FOR_APPROVAL |
| MCS-Q1-20418 | Meridian Cloud Services Corp. | 2026-03-01 | 2026-03-31 | PO-2026-0399 | USD | | true | true | false | EXTRACTED | | |
| NW-88214 | Northwind Office Supplies Inc. | 2026-03-04 | 2026-04-03 | PO-2026-0431 | USD | | true | false | true | POSTED | | |

## 4. Queue: InvoiceQueue_Sagar

The folder holds one queue, InvoiceQueue_Sagar. It was read with `queues list` and `queue-items list` only; no item
was retried, deleted, postponed or changed.

| Setting | Value |
|---|---|
| Name | InvoiceQueue_Sagar |
| Description | Lab 2 invoice work items |
| Max retries | 0 (no automatic retry) |
| Auto-retry on application exceptions | off |
| Retry abandoned items | off |
| Unique reference enforced | yes |
| Folders | 1 (not shared) |
| Total transactions | 5 |

### Items by status

| New | In Progress | Failed | Abandoned | Retried | Successful | Deleted |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 5 | 0 |

### Sample items (all 5, newest first)

Only safe metadata is shown. SpecificContent, Output and OutputData (invoice business data) were not printed or
saved. Each reference is a Data Fabric record id, shortened to its first 8 characters.

| Reference | Status | Created (UTC) | Processing started | Processing ended | Retries | Exception |
|---|---|---|---|---|---|---|
| deb88a48… | Successful | 2026-10-01 21:30:13 | 2026-10-02 19:18:50 | 19:18:51 | 0 | none |
| 3cf3b539… | Successful | 2026-10-01 21:29:48 | 2026-10-02 19:18:49 | 19:18:50 | 0 | none |
| 9de3c02b… | Successful | 2026-10-01 21:29:24 | 2026-10-02 19:18:47 | 19:18:48 | 0 | none |
| 268bc81c… | Successful | 2026-10-01 21:28:59 | 2026-10-02 19:18:46 | 19:18:47 | 0 | none |
| c2f5770d… | Successful | 2026-10-01 21:28:34 | 2026-10-02 19:18:44 | 19:18:46 | 0 | none |

Observation: the Lab 2 intake added the 5 items on 2026-10-01; the Lab 3 queue function processed all of them in
one run on 2026-10-02, about 1 second each. All items were processed by the same robot.

## 5. Operational health: Lab 2-5 processes

Sources: `uip or jobs list --all-fields` per folder (the folder and the solution sub-folder separately),
`uip or triggers list`, and `uip or jobs logs` with levels counted client-side. `jobs get` was not used.
EnvironmentVariables, InputArguments and OutputArguments were never printed or saved, and log messages were
reduced to redacted categories (URLs, paths, ids and amounts stripped). No job was started, stopped or retried.

### Jobs (20 in total, oldest first)

"Version" compares each job's release version with the process's latest: current = ran on today's version.

| Process | Folder | Created (UTC) | State | Duration | Version | Log levels |
|---|---|---|---|---|---|---|
| Invoice_Intake_RPA_Sagar | APAutomation | 10-01 21:27 | Successful | 139 s | earlier | Info 19 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:28 | Successful | 26 s | current (1.0.0) | Info 91, Warn 8 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:28 | Successful | 22 s | current | Info 89, Warn 4 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:29 | Successful | 22 s | current | Info 88, Warn 4 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:29 | Successful | 20 s | current | Info 89, Warn 4 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:29 | Successful | 21 s | current | Info 89, Warn 4 |
| Invoice_Intake_RPA_Sagar | APAutomation | 10-01 21:32 | Successful | 28 s | current (1.0.2) | Info 5 |
| Invoice_Extraction_Agent_Sagar | solution sub-folder | 10-01 21:32 | Successful | 17 s | current | Info 89, Warn 4 |
| POMatch_Sagar_process_invoice_queue | APAutomation | 10-02 19:18 | Successful | 18 s | current (0.0.2) | Info 25, Error 2 (noise) |
| POMatch_Sagar_process_invoice | APAutomation | 10-02 19:19 | Successful | 11 s | earlier | Info 10, Error 2 (noise) |
| POMatch_Sagar_get_invoice_status | APAutomation | 10-02 19:20 | Successful | 12 s | earlier | Info 9, Error 2 (noise) |
| POMatch_Sagar_po_lookup | APAutomation | 10-02 19:20 | Successful | 11 s | current (0.0.2) | Info 9, Error 2 (noise) |
| POMatch_Sagar_process_invoice | APAutomation | 10-02 19:36 | Successful | 11 s | current (0.0.2) | Info 10, Error 2 (noise) |
| PostToERP_Sagar | APAutomation | 10-02 20:25 | Successful | 74 s | current (1.0.0) | Info 14 |
| PostToERP_Sagar | APAutomation | 10-02 20:27 | Successful | 3 s | current | Info 8 |
| Invoice_Approval_Agent_Sagar | APAutomation | 10-02 21:19 | Successful | 36 s | current (0.0.1) | Info 9, Error 4 (noise + deprecation) |
| Invoice_Approval_Agent_Sagar | APAutomation | 10-02 21:20 | Successful | 9 s | current | Info 9, Error 4 |
| Invoice_Approval_Agent_Sagar | APAutomation | 10-02 21:21 | Successful | 8 s | current | Info 9, Error 4 |
| POMatch_Sagar_get_invoice_status | APAutomation | 10-08 19:54 | Successful | 9 s | current (0.0.2) | Info 9, Error 2 (noise) |
| POMatch_Sagar_get_invoice_status | APAutomation | 10-08 19:56 | Successful | 12 s | current | Info 9, Error 2 (noise) |

(Trace-level lines were also present on the function and agent jobs and are not counted above.)

### Runtime, robots and triggers

- All 20 jobs ran on the Serverless runtime and were started manually (source Manual). Serverless hosts are
  allocated on demand (agent runs in a burst shared one host); capacity is the inherited Default Serverless machine (Serverless Total 1, see section 1).
- Triggers: none in APAutomation_Sagar and none in the solution sub-folder; every run so far was manual.

### Highlights

- Faulted, Stopped, Pending, Running or Suspended jobs: **none**. 20 of 20 Successful.
- Longer-than-usual runs (all successful): Invoice_Intake_RPA_Sagar first run 139 s vs 28 s for the second;
  PostToERP_Sagar first run 74 s vs 3 s (the hosted portal has a known 30-60 s cold start);
  Invoice_Approval_Agent_Sagar first run 36 s vs 8-9 s afterwards. Each is the first run of its process.
- Known noise, not faults: "Resource overwrites read from …uipath.json (0 entries)" plus an empty `{}` line, logged
  at Error on every Successful function and coded-agent job.
- Not seen: the Lab 5 governance 403 (policy_service_forbidden) did not appear in these Approval Agent logs.
- Other log lines at Error/Warn: a `FutureWarning` that `uipath.platform.common.constants` is deprecated
  (Approval Agent, logged at Error); extraction agent warnings "Calling end() on an ended span", "Attempting to
  instrument while already instrumented", and on its first run "'id' field not present in uipath.json" and
  "Deserializing unregistered type …".

### Hand-off to uipath-troubleshoot (no root cause attempted here)

1. Invoice_Approval_Agent_Sagar: SDK deprecation `FutureWarning` (uipath.platform.common.constants) logged at
   Error level on every job; check whether the pinned SDK needs an update before it is removed.
2. Invoice_Extraction_Agent_Sagar: repeated tracing warnings (ended span, double instrumentation) on every job,
   plus "'id' field not present in uipath.json" and unregistered-type deserialization warnings on the first run.
3. First-run durations: Intake RPA 139 s and PostToERP 74 s vs a few seconds to half a minute later; confirm this
   is serverless/portal cold start and not a recurring slowdown.
4. Confirm the expected Lab 5 governance 403 is absent because the policy call now succeeds, not because
   logging changed.
