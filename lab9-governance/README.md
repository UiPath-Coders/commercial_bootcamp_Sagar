# Lab 9: governance and admin

This folder starts with only this README. Paste the prompts from the Lab 9 page of the bootcamp site.

## The five steps

| You run | What it does | Creates anything in the tenant? |
|---|---|---|
| Draft the tool-use policy for your Lab 10 caller | Designs a ToolUsePolicy so that only `InvoiceApprovalProcess_<user_name>` may call `Invoice_Approval_Agent_<user_name>` and `PostToERP_<user_name>` | No: it stays a draft file |
| Review your effective tenant access | `check-access` per service, plus Folder scope on `APAutomation_<user_name>` and `Agentic Bootcamp` | No |
| Inventory all tenants and their services | Tenant status, region, provisioned vs available services | No |
| Check the public IP the organization sees | `uip admin ip-restriction my-ip` only | No |
| Commit and push your work | Commits this folder | No |

All five run with participant rights and only inspect or draft. Never create or deploy Automation Ops
policies, access policies, compliance packs, IP ranges, invitations or memberships from this lab.

Your access review will show that the participant group holds Folder Administrator on `Agentic Bootcamp`. That
grant is deliberate (Lab 2 creates your sub-folder under it); report it as a known, accepted grant.

## What the lab writes here

- `access-policy-<slug>.json` and `access-policy-<slug>.spec.md`: the tool-use policy draft. The caller stays
  the literal placeholder `BIND_AFTER_LAB10:InvoiceApprovalProcess_<user_name>`, and the spec explains what
  to bind and deploy after Lab 10. The POMatch functions cannot be governed yet (ToolUsePolicy has no Function
  resource type); the draft says so.
- Short notes from the access review, the tenant inventory and the IP check. Mask the IP (for example
  `170.203.x.x`), and keep emails, tokens and ids out.
- Nothing in `audit-export/`: no Lab 9 step exports audit history. The folder is git-ignored because an audit
  export holds actor emails.
