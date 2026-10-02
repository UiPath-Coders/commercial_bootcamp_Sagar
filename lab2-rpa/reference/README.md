# Lab 2 reference implementations

This folder contains both finished answers for Lab 2. They are intentionally named `_Reference` so they
cannot be confused with a participant's tenant resources.

## Invoice_Extraction_Agent_Reference

A low-code agent definition with:

- one `SourceFile` File input;
- the exact eight string outputs required by the lab;
- a registered IXP tool named `VendorInvoiceIXP`;
- instructions to call that tool once and never invent missing values;
- five simulated evaluation cases using the known invoice answers.

Validate it locally:

```bash
cd Invoice_Extraction_Agent_Reference
uip agent refresh
uip agent validate
uip agent review
```

The expected review is 100/A+.

The project deliberately stores the human-readable IXP binding (`Vendor Invoice <user_name>`, tag `live`)
rather than a tenant model ID. Select the participant's real published model in Studio Web before a live run.

## Invoice_Intake_RPA_Reference

A cross-platform XAML project split into small workflows:

| File | Responsibility |
|---|---|
| `Main.xaml` | batch mode (blank `FileName`): list the bucket, isolate failures per file, summarize; single mode: process exactly `FileName` (the Lab 10 contract) |
| `ProcessInvoiceFile.xaml` | download one file, invoke extraction, validate PO/amount, create, and queue when `in_CreateQueueItem` is True |
| `ExtractInvoiceData.xaml` | run the deployed extraction-agent process and map all eight outputs |
| `CreateInvoiceRecord.xaml` | skip duplicate invoice numbers, create the record, and return its ID |
| `EntityProbe.xaml` | tiny offline entity-type compilation probe used while validating the hand-authored store |

### Main.xaml arguments (the Lab 10 contract)

The contract names deliberately skip the `in_`/`out_` prefixes; the analyzer warnings about that are expected.

| Argument | Direction | Type | Meaning |
|---|---|---|---|
| `FileName` | In | String | Blank = batch over the whole bucket. A file name = process only that file (Maestro, Lab 10). |
| `CreateQueueItem` | In | Boolean | Default True. Single mode adds a queue item only when True and the record is new; batch mode always queues new records. |
| `RecordId` | Out | String | Data Fabric record Id of the single file (existing Id on a duplicate); blank in batch mode. |
| `IsValid` | Out | Boolean | Single: PONumber and a numeric TotalAmount were present. Batch: no file was rejected or failed. |
| `WasDuplicate` | Out | Boolean | Single: the InvoiceNumber already existed, so no record was created. Batch: False. |
| `ErrorMessage` | Out | String | Rejection reason (single) or a rejected/failed count (batch); empty on success. |
| `ProcessedCount` | Out | Int32 | Files processed (1 in single mode). |
| `CreatedCount` | Out | Int32 | Records created. |
| `RejectedCount` | Out | Int32 | Files rejected by the Valid? gate. |

The bucket, queue, agent process and agent folder are `cfg*` variables in `Main.xaml`
(`cfgBucketName`, `cfgBucketDirectory`, `cfgAgentProcessName`, `cfgAgentFolderPath`, `cfgQueueName`), not
arguments, so the Lab 10 contract stays small. Locals use `n*`/`cfg*`/`item*` names so none shadows a contract
argument (VB is case-insensitive).

Validate and compile it locally:

```bash
cd Invoice_Intake_RPA_Reference
uip rpa validate --min-severity warning
uip rpa build
```

The entity store is an offline compilation definition. Before running against a live tenant, bind
`AP_Invoice_Reference` to the participant's `AP_Invoice_<user_name>` entity and replace the reference
bucket, queue, agent-process, and folder settings (the `cfg*` variables in `Main.xaml`) with that participant's
resources.

## What the reference proves

It proves the project structure, workflow arguments, validation gate, Data Fabric field mapping, queue
reference, error isolation, selectors/activity syntax, and package compilation.

It cannot prove a participant's permissions or tenant resource bindings. Those are checked by the live-run
steps in the bootcamp prompt.

## Known defects fixed on 2026-10-02

The dry run found these in the reference. They are fixed in this folder; compare against them if your copy
predates the fix.

- `ExtractInvoiceData.xaml` Run Job had no `FolderPath`, so it looked for the agent in the RPA's own folder.
  It now takes `in_AgentFolderPath`, which `Main.xaml` passes from its `cfgAgentFolderPath` variable,
  `Agentic Bootcamp/APAutomation_Reference/Invoice_Extraction_Agent_Reference`; yours is
  `Agentic Bootcamp/APAutomation_<user_name>/Invoice_Extraction_Agent_<user_name>`.
- The entity store and `CreateInvoiceRecord.xaml` lacked `InvoiceLifecycleState`. The record is now created with
  `InvoiceLifecycleState = "EXTRACTED"`.
- The `Main.xaml` comment said the duplicate check uses "InvoiceNumber + VendorName". The check is by
  `InvoiceNumber` only; the comment is corrected.
- The uipath-agents skill has no IXP tool recipe. To build the IXP tool, copy
  `Invoice_Extraction_Agent_Reference/resources/VendorInvoiceIXP/resource.json` and set `projectName` to the
  display title `Vendor Invoice <user_name>` and `versionTag` to `live`.

## Known defects fixed after the second dry run (2026-10-02)

- `Main.xaml` now carries the Lab 10 contract above (it had `in_*` settings arguments and `out_*` counts only).
  `ProcessInvoiceFile.xaml` takes `in_FileName` and `in_CreateQueueItem`, returns `out_IsValid`,
  `out_WasDuplicate` and `out_ErrorMessage`, and wraps Add Queue Item in `If in_CreateQueueItem`.
- `.entities/EntitiesStore.json` no longer gives POMatched, ApprovalNeeded and PostedToERP a `defaultValue` of
  `false`. Unset means "not decided yet" (Lab 3 reads an unset ApprovalNeeded as true).
