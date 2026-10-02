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
| `Main.xaml` | list the bucket, isolate failures per file, and summarize the run |
| `ProcessInvoiceFile.xaml` | download one file, invoke extraction, validate PO/amount, create and queue |
| `ExtractInvoiceData.xaml` | run the deployed extraction-agent process and map all eight outputs |
| `CreateInvoiceRecord.xaml` | skip duplicate invoice numbers, create the record, and return its ID |
| `EntityProbe.xaml` | tiny offline entity-type compilation probe used while validating the hand-authored store |

Validate and compile it locally:

```bash
cd Invoice_Intake_RPA_Reference
uip rpa validate --min-severity warning
uip rpa build
```

The entity store is an offline compilation definition. Before running against a live tenant, bind
`AP_Invoice_Reference` to the participant's `AP_Invoice_<user_name>` entity and replace the reference
bucket, queue, agent-process, and folder settings with that participant's resources.

## What the reference proves

It proves the project structure, workflow arguments, validation gate, Data Fabric field mapping, queue
reference, error isolation, selectors/activity syntax, and package compilation.

It cannot prove a participant's permissions or tenant resource bindings. Those are checked by the live-run
steps in the bootcamp prompt.

