# Lab 9: solution audit findings

Read-only audit of the invoice-approval solution in `Agentic Bootcamp/APAutomation_Sagar` (tenant Training),
2026-10-08. Nothing in the tenant was created, changed, started or deployed. No secrets, emails or ids here.

Related files in this folder:
- `access-policy-invoice-approval-tool-use-sagar.json` / `.spec.md`: the tool-use policy draft (not created).
  It holds the process Keys the policy needs; the caller stays `BIND_AFTER_LAB10:InvoiceApprovalProcess_Sagar`.
- `access-review.md`: the detailed folder and tenant access review.

## 1. Tool-use policy draft

- Only the Lab 10 Maestro process `InvoiceApprovalProcess_Sagar` may call `Invoice_Approval_Agent_Sagar`
  (Agent) and `PostToERP_Sagar` (RPA). Every other caller falls through to the default deny.
- Starts Simulated. Checked locally (the policy service has no validate). `uip gov access-policy create` not run.
- The four `POMatch_Sagar` functions cannot be governed: ToolUsePolicy has no Function resource type.
- The tenant had no access policies at review time.

## 2. Folder access

| Who | Count | Folder roles | Source |
|-----|-------|--------------|--------|
| Participant group | 1 | Automation Developer, Folder Administrator | Inherited from Agentic Bootcamp |
| Users (me + 8 participants) | 9 | Automation Developer, Folder Administrator | Inherited |
| Other users (likely facilitators) | 2 | Folder Administrator (one also Automation Publisher) | Inherited |
| Robot | 1 | Automation User | Assigned here and inherited |

Flags:
- Participant group is Folder Administrator on Agentic Bootcamp: known, accepted grant (Lab 2 needs it).
- My tenant role set comes mostly from the tenant Administrators group (admin on Orchestrator, Data Service,
  Document Understanding, IXP, Process Mining, Test Manager, licensing). Far broader than the solution needs.
- Three of my groups are unrelated to this solution. Individual participant grants duplicate the group grant.

## 3. Secrets

- Both `.env` files (Lab 3 function, Lab 5 agent) are git-ignored and never appear in the 9 commits.
- Working tree and full history (packages unpacked) hold no real token, signed URL or password. The only hits
  are fake test values in the POMatch tests and the shared mock-portal login from the bootcamp page.
- `ERP_PO_LOOKUP_URL` is set on `POMatch_Sagar_process_invoice` and `_process_invoice_queue`. Its token
  **expired on 2026-10-03**: refresh it from the bootcamp page before Lab 10.
- Housekeeping: Lab 2 committed build packages (`lab2-rpa/dist/`, the extraction-agent zip). No secrets inside.

## 4. Deployment

| Process | Deployed | Repository | Match |
|---------|----------|------------|-------|
| Invoice_Intake_RPA_Sagar | 1.0.2 | 1.0.0 | No: label only, workflows identical to the 1.0.2 package |
| POMatch_Sagar (4 entry points) | 0.0.2 | 0.0.2 | Yes |
| Invoice_Approval_Agent_Sagar | 0.0.1 | 0.0.1 | Yes |
| PostToERP_Sagar | 1.0.0 | 1.0.0 | Yes |

All run serverless. All 14 jobs in the folder were started manually by me (matched to the Orchestrator audit
log). No triggers, no other process, no other user.

## 5. Agent review (when a human gets the case)

| Order | Outcome | Condition | Rule |
|-------|---------|-----------|------|
| 1 | HOLD_PO_MISMATCH | POMatched not true (missing = false) | `approval_gates.py:186-190` |
| 2 | AUTO_APPROVED | ApprovalNeeded false (missing = true) | `approval_gates.py:192-196` |
| 3 | NEEDS_AP_REVIEW | GL Account, Cost Center, Approver or Receipt Reference empty | `approval_gates.py:198-201` |
| 4 | READY_FOR_APPROVAL | all checks passed | `approval_gates.py:203-204` |

- The agent cannot post to the ERP. It only reads and updates its own six fields on one AP_Invoice_Sagar record
  and calls the LLM Gateway for a summary (no tools bound, empty bindings).
- No path approves without a PO match. Flags:
  - AUTO_APPROVED needs no person by design; an empty-text ApprovalNeeded would count as false.
  - The retry guard returns an earlier approval without re-checking POMatched.
  - The agent trusts the stored POMatched / ApprovalNeeded values.
  - PostToERP accepts a caller-supplied `ApprovalConfirmed` flag; the tool-use policy is what limits callers.
