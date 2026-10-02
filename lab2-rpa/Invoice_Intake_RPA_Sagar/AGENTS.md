# Invoice_Intake_RPA_Sagar

Bucket file → `Invoice_Extraction_Agent_Sagar` → validate → `AP_Invoice_Sagar` record (EXTRACTED) → optional `InvoiceQueue_Sagar` item (Reference = RecordId).

- Read `.claude/rules/project-context.md` before editing.
- Gate every change with `uip rpa validate --file-path "<file>.xaml" --project-dir . --output json` and `uip rpa build . --output json`.
- Do not hand-edit `project.json` dependencies or `.entities/`; use `uip rpa packages install` and `uip rpa data-fabric-entities install`.
