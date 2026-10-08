# Lab 10 integration results: InvoiceApprovalProcess_Sagar

Run date: 2026-10-08 (UTC). Synthetic bootcamp data only. Amounts, tax IDs, tokens and signed URLs are deliberately
left out; GUIDs of the deployment are shortened to their first block.

## Deployment (redacted)

| Item | Value |
|---|---|
| Solution / package | `InvoiceApprovalSolution_Sagar` 1.0.0 |
| Deployment name | `InvoiceApprovalSolution_Sagar` (status Active) |
| Deployment folder | `Agentic Bootcamp/APAutomation_Sagar/InvoiceApprovalSolution_Sagar` (key `7c7be8d5-…`) |
| Process | `InvoiceApprovalSolution_Sagar.Agentic.InvoiceApprovalProcess_Sagar` 1.0.0 (release `4035113e-…`) |
| Linked Lab 2-5 processes | Invoice_Intake_RPA_Sagar, POMatch_Sagar_process_invoice, POMatch_Sagar_get_invoice_status, Invoice_Approval_Agent_Sagar, PostToERP_Sagar, all reused from `Agentic Bootcamp/APAutomation_Sagar` (no copies installed) |
| Validation | `uip maestro bpmn validate`: Valid, 0 errors, 2 warnings (FileName process input; `type` attribute on StartJob context inputs) |

## Instance 1: auto-approved path (Step 4)

| Item | Value |
|---|---|
| Instance ID | `793d1b0e-9112-4317-8c01-e5cd948a7b99` |
| Input | `FileName = commercial-invoice-007-liberty-print.pdf` |
| Invoice | LPS-55210, Liberty Print & Signage LLC |
| RecordId (all tasks) | `d2ce6a9a-62c3-f111-bf5b-6045bdd9aec7` |
| Path | Event_start → Task_Intake → Gw_Valid → Task_POMatch → Gw_ApprovalNeeded (No) → Script_NoApproval → Gw_PostJoin → Task_Post → Gw_Posted (Yes) → **End_Paid** |
| Child jobs | Intake `7ab401a6-b70f-4dc7-b671-bf7ac48482df`, PO match `ce099449-04f6-4d7c-a587-1053300d5b46`, Post `4b3b1b4e-8ccd-4185-bbb7-23aafc3cce44` |
| Instance status | Completed (21:50:56 → 21:54:26) |
| Final record | POMatched true, ApprovalNeeded false, PostedToERP true, InvoiceLifecycleState **POSTED** |

## Instance 2: reviewer-approved path (Step 5)

| Item | Value |
|---|---|
| Instance ID | `32c453e3-c463-486c-b8a5-f4fe3d400d98` |
| Input | `FileName = commercial-invoice-009-vertex-analytics.pdf` |
| Invoice | VA-INV-40592, Vertex Analytics Corp. |
| RecordId (all tasks) | `4592ca6a-63c3-f111-bf5b-6045bdd9aec7` |
| Path | Event_start → Task_Intake → Gw_Valid → Task_POMatch → Gw_ApprovalNeeded (Yes) → Task_Agent → Gw_AgentResult (Review) → Gw_WaitJoin → Timer_Wait (PT2M) → Script_CountPoll → Task_Status → Gw_Approved (APPROVED) → Script_Approved → Gw_PostJoin → Task_Post → Gw_Posted (Yes) → **End_Paid** |
| Child jobs | Intake `71f42473-37f5-48b8-a8ff-69b3d35af725`, PO match `bb8da3eb-483a-4e61-a1a3-1413213ccce4`, Agent `6b3a8b7f-ddd8-46d2-8679-caa8b0a47e29`, Status `c2e796af-bd72-42e3-a346-9b8c67cbfd8d`, Post `aaeeebaa-7023-4395-a749-cceab2253f72` |
| Review wait | Waited in NEEDS_AP_REVIEW; first live PT2M timer cycle ran, PollCount 1; status read saw APPROVED |
| Reviewer | Approved by the participant in ap-approval-review-Sagar (ReviewedAt 2026-10-08T22:02:47Z) |
| Posting | PostToERP_Sagar called with the same RecordId and ApprovalConfirmed true; Posted true, WasAlreadyPosted false |
| Instance status | Completed (21:57:26 → 22:03:38) |
| Final record | POMatched true, ApprovalNeeded true, PostedToERP true, InvoiceLifecycleState **POSTED** |

Note: during the review a second click also approved the Lab 5 eval row TRAIN-VA-1006 (no instance was waiting on
it, so it was not posted). It was reset to READY_FOR_APPROVAL with ReviewedBy/ReviewedAt cleared at the
participant's request; all other pre-existing records match their pre-run state.

## Debug run (Step 2)

One `uip maestro bpmn debug` of the happy path with `commercial-invoice-001-northwind.pdf` (record already POSTED)
ended at End_Paid without creating a record. It left Studio Web solution `7aa82d79-…` for cleanup.
