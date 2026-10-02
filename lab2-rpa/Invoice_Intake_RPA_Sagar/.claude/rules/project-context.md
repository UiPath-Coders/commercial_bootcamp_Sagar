<!-- project-context: workflows=2 entities=1 generated=2026-10-01 -->
# Invoice_Intake_RPA_Sagar — project context

- Cross-platform (`Portable`), VisualBasic expressions, XAML only. Packages: UiPath.System.Activities 26.8.2, UiPath.DataService.Activities 26.10.1.
- `Main.xaml` (entry point) → `ProcessInvoiceFile.xaml` (one file, reusable). No other workflows.
- Data Fabric: `AP_Invoice_Sagar` (tenant scope, Id `5c5aadee-d6bd-f111-a6a9-6045bddc9767`) installed via `uip rpa data-fabric-entities install`; field GUIDs come from `.entities/EntitiesStore.json`. Re-run the install after any schema change.
- Orchestrator bindings (variables in `Main.xaml`): bucket `InvoiceInbox_Sagar` and queue `InvoiceQueue_Sagar` in `Agentic Bootcamp/APAutomation_Sagar`; agent process `Invoice_Extraction_Agent_Sagar` in `Agentic Bootcamp/APAutomation_Sagar/Invoice_Extraction_Agent_Sagar` (Run Job, dictionary arguments: `SourceFile` in, eight string outputs).
- Entry-point argument names (`FileName`, `CreateQueueItem`, `RecordId`, …) intentionally skip the `in_`/`out_` prefix — they are the public contract for Lab 3 / Lab 10; the analyzer naming warnings are expected.
- Conventions: `in_`/`out_` prefixes on internal workflow arguments; every container body wrapped in `Sequence`; InvokeWorkflowFile arguments as direct children (no Dictionary wrapper).
