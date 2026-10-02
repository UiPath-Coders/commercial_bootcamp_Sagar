# Canonical Day 2 Handoff

## Repository

- Lab 5 starter: `UiPath-Coders/commercial_bootcamp_lab_assets` → `lab5-coded-agent/`
- Participant: `<user_name>`

## UiPath resources

| Value | Verified result |
| --- | --- |
| Folder name | `APAutomation_<user_name>` |
| Folder key | `<FOLDER_KEY>` |
| Queue name | `InvoiceQueue_<user_name>` |
| Entity name | `AP_Invoice_<user_name>` |
| Entity ID | `<ENTITY_ID>` |
| Entity key | `<ENTITY_KEY>` (= Entity ID; the SDK calls it entity_key) |
| Canonical record ID | `<CANONICAL_RECORD_ID>` |

## Day 1 evidence

| Check | Status | Evidence reference |
| --- | --- | --- |
| Queue Reference equals canonical record ID | `<STATUS>` | `<SANITIZED_REFERENCE>` |
| POMatched verified from Lab 3 | `<STATUS>` | `<SANITIZED_REFERENCE>` |
| ApprovalNeeded verified from Lab 3 | `<STATUS>` | `<SANITIZED_REFERENCE>` |

## Lab 5 evidence

| Value | Result |
| --- | --- |
| Agent project | `agent/` |
| Agent name | `Invoice_Approval_Agent_<user_name>` |
| Recommendation | `<AGENT_RECOMMENDATION>` |
| Lifecycle state | `<INVOICE_LIFECYCLE_STATE>` |
| Deployment reference | `<SANITIZED_DEPLOYMENT_REFERENCE>` |

## Lab 6 evidence

| Value | Result |
| --- | --- |
| App name | `ap-approval-review-<user_name>` |
| Deployment URL | `<SANITIZED_APP_URL>` |
| Reviewer decision | `<APPROVED or REJECTED>` by `<user_email>` at `<REVIEWED_AT>` |

Do not record tokens, secrets, vendor tax IDs, bank details, or invoice amounts.
