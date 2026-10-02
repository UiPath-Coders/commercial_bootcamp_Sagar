# Lab 10 — orchestrate the whole invoice process with Maestro BPMN

**What you build:** `InvoiceApprovalProcess_<user_name>.bpmn` inside the solution
`InvoiceApprovalSolution_<user_name>`. It is the executable version of the process diagram on the bootcamp
site: one Maestro instance takes one invoice file from intake to Paid, calling the components you already built
and tested in Labs 2-6. Nothing from earlier labs is rebuilt.

| BPMN step | Calls | Built in |
|---|---|---|
| Intake invoice | `Invoice_Intake_RPA_<user_name>` (FileName, CreateQueueItem false) | Lab 2 |
| `Valid?` gateway | IsValid from intake | |
| PO match | `POMatch_<user_name>_process_invoice` (record_id) | Lab 3 |
| `Approval needed?` gateway | approval_required from process_invoice | |
| Prepare approval | `Invoice_Approval_Agent_<user_name>` (recordId) | Lab 5 |
| Human-review wait | PT2M timer, then PollCount + 1, then `POMatch_<user_name>_get_invoice_status` | Lab 3 |
| `Approved?` gateway | invoice_lifecycle_state written by the reviewer in `ap-approval-review-<user_name>` | Lab 6 |
| Post to ERP | `PostToERP_<user_name>` (RecordId, ApprovalConfirmed, PortalUrl) | Lab 4 |

Ends: Invalid Invoice, Held, Rejected, Paid, Operational Failure. Every service task has an error boundary that
goes to Operational Failure.

**How you build it:** in the Claude Code desktop app, on your own copy of this repo, paste the prompts from the
Lab 10 page of the bootcamp site. The first prompt runs a read-only readiness check of every component.

## Before you start

All of these live in `Agentic Bootcamp/APAutomation_<user_name>` and must be Ready in the Step 1 readiness table:

- `Invoice_Intake_RPA_<user_name>` with its Run Job pointing at the extraction agent's solution folder;
  `Vendor Invoice <user_name>` live behind `Invoice_Extraction_Agent_<user_name>`.
- `POMatch_<user_name>_process_invoice` and `POMatch_<user_name>_get_invoice_status`, each bound to its own entry
  point. `process_invoice` must carry the process-level environment variable `ERP_PO_LOOKUP_URL`: Maestro cannot
  pass job environment variables, so without it the function calls `http://localhost:8080` and returns
  `ERP_UNREACHABLE`.
- `Invoice_Approval_Agent_<user_name>` (processType Agent) with the `recordId` input.
- `PostToERP_<user_name>` and the hosted portal URL `https://commercial-bootcamp-mock-erp.onrender.com/portal/`.
- `ap-approval-review-<user_name>` deployed at its latest version, and `InvoiceLifecycleState` on
  `AP_Invoice_<user_name>`.

## The runtime rules

Every one of these passes `uip maestro bpmn validate` when broken, and every one fails at runtime. They were
found in the 2026-10-02 dry run with `uip maestro bpmn debug`, and the reference follows all of them.

1. **StartJob context inputs carry `type="string"`, and `releaseKey` is a literal process key.** A registry
   template without `type`, or a `releaseKey` taken from `=bindings.…`, fails with
   `170005 … Required field 'releaseKey' missing in the input args to RPA task`.
2. **Call the agent with `Orchestrator.StartJob` and its release key.** `Orchestrator.StartAgentJob` cannot run:
   the validator forbids `releaseKey` and the runtime requires it.
3. **No underscores in variable ids** (`VarRecordId`, never `Var_RecordId`). Underscores are stripped at
   runtime and the mappings stop matching.
4. **Set variables with `BPMN.Variables` and a `custom="true"` output** with `source="=js:…"`. A
   `BPMN.ScriptTask` with `source="=result.response"` never sets the target variable.
5. **Give every task a `<uipath:inputSchema type="jsonSchema">`** and map each output argument on its own
   (`<uipath:output name="po_matched" source="=po_matched" …>`). This works for snake_case function outputs and
   camelCase agent outputs.

Also:

- Pack and refresh do not generate `entry-points.json` (the FileName input) or `bindings_v2.json` (v2.2, name +
  folderPath per process). Write both by hand from the BPMN, then refresh.
- Timer loop: PT2M, then PollCount + 1, then get_invoice_status (the reference order). Loop while the state is NEEDS_AP_REVIEW or
  READY_FOR_APPROVAL and PollCount is below 6 (about 13 minutes); at 6 end as Held. Never use PT30S: each cycle
  starts a serverless job.

## Package, deploy, run

- **Strip secrets before pack.** `uip solution resources refresh` copies process environment variables, including
  the signed ERP URL, into `resources/…json`, and a second refresh does not update them. Search `resources/` for
  `access_token`, `ERP_PO_LOOKUP_URL` and `environmentVariables`, clear them with
  `uip solution resources edit <key> --patch '{"environmentVariables":""}'`, and search the zip again after pack.
- **Link the five Lab processes.** The default deploy config installs copies of all five in the new solution
  folder. Run `uip solution deploy config link <config> <name> --name <name> --folder-path "Agentic Bootcamp/APAutomation_<user_name>"`
  once per process before `deploy run`.
- **No upgrade.** A deploy always creates its own child folder, and uip 1.200.1 has no `deploy upgrade`. A new
  version is a new deployment (for example `InvoiceApprovalSolution_<user_name>_v101`) in a sibling folder; the
  facilitator removes the old one.
- **Monitor with element executions.**
  `uip maestro bpmn instance element-executions <instance-id> --folder-key <solution-folder-key>` is the only live
  view: `job traces` prints nothing and `instance global-variables` returns 404 while the instance runs, and a
  failed instance's Maestro job can still show Successful. Live variables (PollCount) come from
  `uip maestro bpmn instance variables <instance-id> --folder-key <solution-folder-key>` → `Data.Globals`.
- **Reviewer path.** Approve VA-INV-40592 (Vertex Analytics Corp.) in your app, found by InvoiceNumber and
  VendorName. Do not touch TRAIN-VA-1006, a Lab 5 evaluation row from the same vendor. The instance resumes within
  one timer cycle (about 2 minutes).

## What is in this folder

| Path | What it is |
|---|---|
| `reference/README.md` | How the reference is laid out, what to replace before it can run, and what was and was not proven. |
| `reference/InvoiceApprovalSolution_Reference/` | The reference solution: `.uipx` manifest and the `InvoiceApprovalProcess_Reference` project (BPMN, `entry-points.json`, `bindings_v2.json`, project metadata). |

## Done means

- the auto-approved invoice (007, Liberty Print) runs Intake → Valid → PO match → Post → Paid with one RecordId
  and ends POSTED, without the agent or the app;
- the reviewer invoice (009, Vertex Analytics) waits in the timer loop, resumes after your approval, and ends Paid
  with the same record POSTED;
- `Agentic Bootcamp/APAutomation_<user_name>` still holds exactly one copy of each Lab 2-5 process;
- no token appears in the solution files, the zip, or the commit; the `.uipx` manifest is committed and build
  zips are not.
