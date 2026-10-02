# Lab 2 — turn invoice files into canonical records

Lab 1 taught an IXP model to read an invoice. Lab 2 turns that model into a working intake pipeline.

Your coding agent builds two projects:

1. `Invoice_Extraction_Agent_<user_name>` receives one file, calls the live Lab 1 IXP model, and returns
   eight strings.
2. `Invoice_Intake_RPA_<user_name>` reads the storage bucket one file at a time, calls the agent, rejects
   structurally incomplete results, creates one Data Fabric record, and queues that record's ID.

That Data Fabric record ID—not the filename or queue transaction ID—is the invoice's identity for Labs 3–6.

## What you have before writing code

| Path | Purpose |
|---|---|
| `invoice001.pdf` … `invoice005.pdf` | the five Day 1 invoice files uploaded to the storage bucket |
| `emails/` | the corresponding vendor emails with the same PDFs attached |
| `reference/Invoice_Extraction_Agent_Reference/` | a complete low-code agent definition, IXP resource registration, and five evaluation cases |
| `reference/Invoice_Intake_RPA_Reference/` | a complete cross-platform XAML intake process |
| `reference/README.md` | a map of both answers and the exact validation commands |

Everything is synthetic.

## Start the lab

Work in your private participant repository, not in the golden asset repository:

```text
Work inside commercial_bootcamp_<user_name>/lab2-rpa for the rest of this session. List the files you find.
```

Then follow the prompts on the Lab 2 bootcamp page. They are the source of truth for names, fields, and
deployment steps.

## The contract your projects must match

The extraction agent has one input:

- `SourceFile` — File

It has exactly these eight string outputs:

- `VendorName`
- `VendorTaxId`
- `InvoiceNumber`
- `InvoiceDate`
- `PONumber`
- `TotalAmount`
- `Currency`
- `DueDate`

The RPA process accepts an invoice only when `PONumber` and `TotalAmount` are present and the amount is
numeric. A rejected invoice is logged and creates neither a Data Fabric record nor a queue item.

For a valid invoice, create `AP_Invoice_<user_name>` with the eight extracted values plus
`ProcessedTimestamp`. Leave `POMatched`, `ApprovalNeeded`, and `PostedToERP` unset; later labs own those
fields. Capture the new record ID and use it as the queue item's reference.

The reference also checks for an existing `InvoiceNumber` before creating a record, making a rerun safe.

## What runs locally

The low-code project can be refreshed, validated, and reviewed from the clone. The RPA project can be
validated and compiled from the clone. The invoice files and all expected values are present locally.

A real extraction run still needs the participant's published Lab 1 IXP model. Bind the agent's
`VendorInvoiceIXP` resource to the participant's `Vendor Invoice <user_name>` project and its `live` tag in
Studio Web. The storage bucket, queue, Data Fabric entity, folder, and deployed process are also
participant-owned tenant resources.

## Quick reference check

```bash
cd reference/Invoice_Extraction_Agent_Reference
uip agent refresh
uip agent validate
uip agent review

cd ../Invoice_Intake_RPA_Reference
uip rpa validate --min-severity warning
uip rpa build
```

Expected result: agent validation succeeds and review is 100/A+; the RPA project reports no validation
diagnostics and builds `true`. A tenant policy may add an Automation Hub URL warning.

## Done means

- all five files were processed independently;
- missing PO number or total amount was rejected without downstream writes;
- each valid invoice created exactly one record;
- each queue reference equals the created Data Fabric record ID;
- the three later-lab booleans remain unset;
- both local reference checks pass;
- the participant's project is committed and pushed.

## Common mistakes

- Passing a local path as the agent input. The deployed agent expects a UiPath File/job attachment.
- Returning numbers or dates instead of the eight required strings.
- Treating a failed extraction as valid because some fields were populated.
- Using the queue transaction ID as the canonical invoice ID.
- Hard-coding the reference entity GUID or another participant's resource IDs.
