# Policy Spec: Invoice Approval Tool Use Sagar

**Status of this file:** draft only. Nothing has been created or deployed in the tenant.
`uip gov access-policy create` was not run. The JSON payload sits next to this file:
`access-policy-invoice-approval-tool-use-sagar.json`.

Scope: organization `customersuccessamer` / tenant `Training` (staging.uipath.com).

## Narrative

Only the Lab 10 Maestro process `InvoiceApprovalProcess_Sagar` may invoke the coded agent
`Invoice_Approval_Agent_Sagar` and the RPA process `PostToERP_Sagar` in `Agentic Bootcamp/APAutomation_Sagar`.
Any other caller (another Maestro process, a Flow, a Case or an Agent) gets no Allow from this policy and falls
through to the runtime default, which denies the call for these two resources. No identity restriction applies:
whoever runs the Maestro process passes. The `POMatch_Sagar` functions are not covered, because ToolUsePolicy has
no Function resource type. The policy starts in Simulated mode.

## Spec Components Table

| # | Component | Value |
|---|-----------|-------|
| 1 | Name | Invoice Approval Tool Use Sagar |
| 2 | Description | The narrative above (shortened in the JSON) |
| 3 | Status | Simulated (evaluated and logged, not enforced) |
| 4 | Enforcement | Allow (the only authorable value; Deny is the runtime default for unmatched callers) |
| 5 | Resource type | Agent; RPA (two separate selector entries) |
| 6 | Resource scope | Agent: `Invoice_Approval_Agent_Sagar` only. RPA: `PostToERP_Sagar` only |
| 7 | Resource tag filter | (none) |
| 8 | Actor Process type | Maestro |
| 9 | Actor Process scope | `InvoiceApprovalProcess_Sagar` only, as placeholder `BIND_AFTER_LAB10:InvoiceApprovalProcess_Sagar` |
| 10 | Actor Process tag filter | (none) |
| 11 | Actor Identity type | (none = any identity) |
| 12 | Actor Identity scope | (none) |

## Affected resources (resolved live in `Agentic Bootcamp/APAutomation_Sagar`)

| Name | Orchestrator type | Policy type | Process Key | Version | In this policy |
|------|-------------------|-------------|-------------|---------|----------------|
| Invoice_Approval_Agent_Sagar | Agent | Agent | `2CB7C282-4FE3-4B25-B1AA-D29AA944FE66` | 0.0.1 | Protected resource |
| PostToERP_Sagar | Process | RPA | `CE50297F-925F-40D6-8D07-E879A76A0EAA` | 1.0.0 | Protected resource |
| POMatch_Sagar_get_invoice_status | Function | (none) | n/a | 0.0.2 | Cannot be governed |
| POMatch_Sagar_process_invoice | Function | (none) | n/a | 0.0.2 | Cannot be governed |
| POMatch_Sagar_process_invoice_queue | Function | (none) | n/a | 0.0.2 | Cannot be governed |
| POMatch_Sagar_po_lookup | Function | (none) | n/a | 0.0.2 | Cannot be governed |
| Invoice_Intake_RPA_Sagar | Process | RPA | n/a | 1.0.2 | Out of scope (not requested) |
| InvoiceApprovalProcess_Sagar | (not created yet) | Maestro | placeholder | n/a | The only allowed caller |

Keys come from `uip or processes list --folder-path "Agentic Bootcamp/APAutomation_Sagar"` on 2026-10-08.
At draft time the tenant had no access policies at all (`uip gov access-policy list` → TotalCount 0), so nothing
overlaps with this draft.

## Scenarios

| # | Caller | Calls | Expected once Active and bound |
|---|--------|-------|--------------------------------|
| A1 | Maestro `InvoiceApprovalProcess_Sagar` | Invoice_Approval_Agent_Sagar | **Allow** |
| A2 | Maestro `InvoiceApprovalProcess_Sagar` | PostToERP_Sagar | **Allow** |
| D1 | Any other Maestro process (e.g. another participant's, or a Lab 10 debug copy with its own key) | Either resource | **Deny** |
| D2 | Any Flow (e.g. the Challenge Maestro Flow) | Either resource | **Deny** |
| D3 | Any Agent (e.g. Invoice_Extraction_Agent_Sagar, or an agent using these as tools) | Either resource | **Deny** |
| D4 | Any Case Management process | Either resource | **Deny** |
| N1 | Any caller | POMatch_Sagar_* functions | Not governed (no Function resource type) |
| N2 | A person or trigger starting the job directly in Orchestrator (not a tool call) | Either resource | Not governed: ToolUsePolicy only gates process-to-process tool use |

Note: a new deployment of the Lab 10 solution gets a new process Key. Each redeploy needs the key re-bound
(see below), otherwise the new caller falls under D1.

## Proposed rules (JSON, from the plugin shapes)

```json
"selectors": [
  { "resourceType": "Agent",       "values": ["2CB7C282-4FE3-4B25-B1AA-D29AA944FE66"], "operator": "Or" },
  { "resourceType": "RPAWorkflow", "values": ["CE50297F-925F-40D6-8D07-E879A76A0EAA"], "operator": "Or" }
],
"executableRule": {
  "values": [
    { "type": "AgenticProcess", "values": ["BIND_AFTER_LAB10:InvoiceApprovalProcess_Sagar"], "operator": "Or" }
  ]
},
"enforcement": "Allow",
"status": "Simulated"
```

No `actorRule`: the request names no user or group restriction.

## Why the POMatch functions are not covered

ToolUsePolicy resource types are Agent, Maestro, RPA, API Workflow, Case Management and Flow. There is no
Function type, so `POMatch_Sagar_get_invoice_status`, `_process_invoice`, `_process_invoice_queue` and
`_po_lookup` cannot be selected. Any caller can still start them. Revisit when the policy service adds a
Function resource type.

## Local check (no server-side validate exists)

The policy service has no validate endpoint, so the JSON was checked locally:
valid JSON; `policyType` ToolUsePolicy; `enforcement` Allow (no Deny anywhere); `status` Simulated; each
selector has one resource type, a non-empty `values` and operator Or; selector keys equal the live process Keys
above; the caller type is AgenticProcess (RPA/API are never callers); the only caller value is the placeholder;
no `actorRule`; no server-managed fields (`id`, `createdOn`, …).

## What must be bound and deployed after Lab 10

1. **Finish Lab 10.** Deploy the solution so `InvoiceApprovalProcess_Sagar` exists as a process in its solution
   folder under `Agentic Bootcamp/APAutomation_Sagar`.
2. **Resolve the caller's process Key.** `uip or folders list --limit 200` → find the Lab 10 solution folder;
   then `uip or processes list --folder-path "<that folder path>" --process-type ProcessOrchestration --name InvoiceApprovalProcess_Sagar --all-fields --output json`.
   Confirm `ProcessType` is `ProcessOrchestration` and take its `Key` (a UUID).
3. **Bind.** In the JSON, replace `BIND_AFTER_LAB10:InvoiceApprovalProcess_Sagar` with that Key. Change nothing
   else.
4. **Re-check the protected keys.** Run the `processes list` on `Agentic Bootcamp/APAutomation_Sagar` again.
   If Lab 10's deploy config linked the existing processes (the documented `deploy config link` step), the keys
   above stay valid. If it installed copies, the solution's agent and PostToERP have new keys: add or swap
   them in the two selectors.
5. **Create in Simulated.** `uip gov access-policy create --file access-policy-invoice-approval-tool-use-sagar.json --output json`
   (only with facilitator approval: Lab 9 never creates policies). Record the returned policy id.
6. **Evaluate with real keys.** `uip gov access-policy evaluate` with `--actor-process-type AgenticProcess`
   and `--actor-process-id <caller Key>` against each resource (expect Allow), and with another process Key, e.g.
   a Flow (expect Deny in the simulated verdict). Tenant-scoped login is required.
7. **Activate.** Update the policy with `status: "Active"`, then run one Lab 10 instance end to end and confirm
   both tool calls still succeed.
8. **Rebind on every redeploy.** A new Lab 10 deployment (`_v101` sibling folder) has a new Key; update the
   caller value, or the new instance is denied.
