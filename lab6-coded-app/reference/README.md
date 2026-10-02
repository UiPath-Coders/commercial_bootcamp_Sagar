# Lab 6 reference

`ap-approval-review/` is the complete answer for Lab 6: a React + TypeScript + Vite Coded Web App on the
`@uipath/uipath-typescript` SDK. Its own `ap-approval-review/README.md` covers the screens, the local run, the
pack / publish / deploy commands and the design notes. This page lists what to check first when you compare.

## The approval rule

Enforced in `ap-approval-review/src/data/invoiceModel.ts#decisionAvailability`:

| InvoiceLifecycleState | ApprovalNeeded | Approve | Reject | Note in the detail panel |
|---|---|---|---|---|
| READY_FOR_APPROVAL | true | enabled | enabled | none |
| NEEDS_AP_REVIEW | true | enabled | enabled | one line: approval evidence is incomplete, with MissingApprovalFields |
| either of the above | not true | disabled | disabled | agent inconsistency, rerun the Lab 5 agent |
| AUTO_APPROVED, HOLD_PO_MISMATCH, APPROVED, REJECTED, POSTED, empty | any | disabled | disabled | why no decision is possible |

Approve writes APPROVED, Reject writes REJECTED; both write ReviewedBy (the signed-in email) and ReviewedAt on
the same `AP_Invoice_<user_name>` record. Lab 10's `Approved?` gateway trusts that write and posts an
approved invoice even when its evidence was incomplete, so the reviewer, not the app, owns that call.

## The "Approval required" column and the approval package

- The table's **Approval required** column (`approvalPill` in `invoiceModel.ts`) shows an amber **Needed** pill
  only while ApprovalNeeded is true and InvoiceLifecycleState is EXTRACTED, NEEDS_AP_REVIEW,
  READY_FOR_APPROVAL or empty. Once the state is APPROVED, REJECTED or POSTED it shows a neutral pill with the
  decision word (Approved, Rejected, Posted), so a decided row no longer reads as outstanding.
- The detail panel renders ApprovalPackageJson as a readable package (`components/ApprovalPackageView.tsx`):
  the agent narrative as a paragraph, an evidence checklist of the seven approval inputs with
  MissingApprovalFields highlighted, a PO-match summary (matched, open amount, reason), the reviewer note when
  present, and the raw JSON behind a collapsed **View raw JSON** toggle. It tolerates differently named keys,
  because each participant's agent shapes the package its own way.

When you approve, find the row by InvoiceNumber and VendorName. The table has no Record ID column, and Lab 5
evaluation rows (TRAIN-*) can share a vendor with the invoice you mean.

## How the reference differs from your app

- **Entity id placeholder.** The reference reads the entity by id from `src/config/uipath.ts`
  (`REPLACE_WITH_AP_INVOICE_ENTITY_ID`) and writes with `entities.updateRecordById`, which is deprecated in SDK
  1.7.2. Today's prompt has you address the entity by name (`getByName`, `getRecordsByName`,
  `getRecordByName`, `updateRecord({ name }, id, patch)`), so your app has no id to edit.
- **Pinned versions.** The reference pins React 18, Vite 5, TypeScript 5.4 and SDK ^1.5.3. Today's
  create-vite scaffold produces React 19, Vite 8, TypeScript 6 and SDK 1.7.2.
- **Page size** is 5, so the seeded records span several pages.

## Check it locally

```bash
cd ap-approval-review
npm install
npm run type-check
npm run build
```

`npm run build` must pass. The live run needs the entity id in `src/config/uipath.ts` and a signed-in session
on Training (see the app README).
