# ap-approval-review — Lab 6 reference solution (facilitators)

Reference implementation of the **Review & Approve** step of the Commercial Bootcamp process
(Office of the CFO · Invoice-to-Pay Approval): the AP reviewer **UiPath Coded Web App** that
participants build in Lab 6. It is a real Vite + React + TypeScript app on the
`@uipath/uipath-typescript` SDK that reads and writes the participant's tenant-scoped
`AP_Invoice_<user_name>` Data Fabric entity. All data is synthetic; nothing here is a credential.

- This folder is named `ap-approval-review`. **Participants name theirs `ap-approval-review-<user_name>`**
  (their first name), and pack / publish / deploy under that name so apps do not collide in the shared
  `customersuccessamer / Training` tenant.
- Canonical spec: `bootcamp-site/docs/commercial-process.md`. Lab text: `bootcamp-site/src/data/labs/lab6.ts`.
- No mock mode, no embedded tokens, no second data store. The only data source is the entity, through
  the authenticated SDK session.

## What it does

| Screen | Behaviour |
|---|---|
| Sign-in | `Sign in with UiPath` starts the PKCE flow (`sdk.initialize()`). Auth errors render inline with a retry. |
| **Screen 1 — gate** | Shown only after a successful login. `winner.png` + the text of `message.txt`, one button **Yes, I am winner**. UiPath sign-in blue on cool neutrals, no headings/icons/extra copy. |
| **Screen 2 — worklist** | Header, KPI strip, data-integrity banner, search, sortable table with column coverage rings, pagination (5/page, "Showing X–Y of Z"), refresh, invoice-detail slide-over with **Approve / Reject**. |

KPI definitions (from the spec):

| Card | Definition | Chart |
|---|---|---|
| Total Invoices | loaded rows | sparkline of new invoices per day, last 7 days (`ProcessedTimestamp`, fallback `CreateTime`) |
| Approval Needed | `ApprovalNeeded = true` | donut vs total |
| Pending Review | `InvoiceLifecycleState ∈ {NEEDS_AP_REVIEW, READY_FOR_APPROVAL}` | donut vs total |
| Recommended for Approval | `AgentRecommendation = READY_FOR_APPROVAL` | donut vs total |

A card whose backing field is absent from the **live schema** renders an explicit empty state (dashed
outline, muted value, caption naming the field) rather than `0`.

Decision rules (the "Approved?" gateway), enforced in `src/data/invoiceModel.ts#decisionAvailability`:

```
Approve : NEEDS_AP_REVIEW | READY_FOR_APPROVAL  -> APPROVED
Reject  : NEEDS_AP_REVIEW | READY_FOR_APPROVAL  -> REJECTED   (one-line reason -> ApprovalPackageJson.reviewerNote)
Both    : ReviewedBy = signed-in email, ReviewedAt = ISO now   (entities.updateRecordById on the SAME record)
Both additionally require ApprovalNeeded = true.
NEEDS_AP_REVIEW shows a one-line note that approval evidence is incomplete (MissingApprovalFields).
AUTO_APPROVED / HOLD_PO_MISMATCH / APPROVED / REJECTED / POSTED / empty -> buttons disabled with a one-line explanation.
```

The table's **Approval required** column shows an amber **Needed** pill only while ApprovalNeeded is true and
the state is EXTRACTED, NEEDS_AP_REVIEW, READY_FOR_APPROVAL or empty; after APPROVED, REJECTED or POSTED it
shows a neutral pill with the decision word (`approvalPill` in `src/data/invoiceModel.ts`).

After a successful write the response is merged into the local row, so the table and panel update without a
full reload. Write errors show inline with retry; a 401 offers "Sign in again".

## Run locally

Prerequisites: Node 18+ (built with Node 26 / npm 11), a UiPath account on `customersuccessamer / Training`
(staging), and the entity id configured (next section).

```bash
npm install --@uipath:registry=https://registry.npmjs.org   # the registry flag bypasses any GitHub-Packages @uipath scope in ~/.npmrc
npm run dev                                                   # http://localhost:5173
```

**Port 5173 matters.** `uipath.json` sets `redirectUri: http://localhost:5173`, and that is the redirect
registered on the shared external OAuth application (`clientId 9e626cd7-…`, same client as the lab tracker and
the manager dashboard). If Vite falls back to another port (5174…), sign-in will fail with a redirect
mismatch — stop whatever holds 5173 first (`lsof -nP -iTCP:5173 -sTCP:LISTEN`). The OAuth client, scopes,
org, tenant and base URL in `uipath.json` are copied verbatim from `bootcamp-site/uipath.json`; the
`@uipath/coded-apps-dev` Vite plugin injects them as `<meta name="uipath:*">` tags in dev, and the platform
injects them in production. Scopes: `DataFabric.Schema.Read DataFabric.Data.Read DataFabric.Data.Write OR.Users.Read`.

Other scripts: `npm run type-check` (tsc, no emit) · `npm run build` (tsc + vite → `dist/`) · `npm run preview`.

## Configure the entity id

The app reads the entity id from **`src/config/uipath.ts`**, which ships with a documented placeholder.
Until it is replaced the app shows a "Entity id not configured" page after login instead of the gate.

```bash
uip login --authority https://staging.uipath.com/identity_ --organization customersuccessamer --tenant Training
uip df entities list --output json          # copy the "id" GUID of the row named AP_Invoice_<user_name>
uip df entities get <ENTITY_ID> --output json   # optional: confirm the Lab 5 fields exist
```

Edit `INVOICE_ENTITY_ID` in `src/config/uipath.ts`, then `npm run dev` / `npm run build`.
Leave `invoiceFolderKey` empty: `AP_Invoice_<user_name>` is **tenant-scoped**; passing the deployment folder
key to Data Fabric calls is the "not found only when a folder is supplied" failure from the lab. The folder key
belongs only on `uip codedapp deploy`.

Field names are the PascalCase system names from the spec (`src/data/invoiceFields.ts`); Data Fabric record
keys are case-sensitive and unknown keys are silently dropped on update, so do not re-case them.

## Lab steps → files

| Lab 6 step | Where it lives |
|---|---|
| 2 · Confirm the schema | `src/data/schema.ts` — `entities.getById(entityId)` at runtime; drives the data-integrity banner, KPI empty states, column coverage `n/a`, and disables decisions when `InvoiceLifecycleState` / `ReviewedBy` / `ReviewedAt` are missing. |
| 3 · Scaffold + OAuth | `package.json`, `vite.config.ts` (`base: './'`, `uipathCodedApps()` plugin), `uipath.json`, `.uipath/project.json`, `src/auth/AuthProvider.tsx` (`new UiPath()`, `isInOAuthCallback` → `completeOAuth`, StrictMode guard, signed-in email via `ConversationalAgent.user.getSettings()`). |
| 4 · Screen 1 gate page | `src/screens/GatePage.tsx`, `public/winner.png`, `src/assets/message.txt` (imported `?raw`), `.gate*` styles in `src/styles/globals.css`. |
| 5 · Screen 2 worklist | `src/screens/Worklist.tsx` (layout, banners, search, states) · `src/components/KpiStrip.tsx` + `Charts.tsx` (four cards, sparkline/donut, empty states) · `src/components/InvoiceTable.tsx` (columns, pills, coverage rings, copy-id on hover, pagination) · `src/components/InvoiceDetailPanel.tsx` (five field groups, Approve/Reject behind a confirmation that names the InvoiceNumber and VendorName, reject reason) · `src/components/EvaluationTag.tsx` ("Evaluation data" tag on TRAIN- rows) · `src/components/ApprovalPackageView.tsx` (readable `ApprovalPackageJson`: narrative, evidence checklist, PO-match summary, reviewer note, collapsed raw JSON) · `src/data/useInvoices.ts` (cursor loop, search, sort, page, coverage, KPIs) · `src/data/useReviewDecision.ts` (the write) · `src/data/invoiceModel.ts` (typed mapping, decision rules, formatting) · `src/data/errors.ts` (auth / forbidden / not-found / service). |
| 6 · Run locally, first decision | `npm run dev`; approve the Lab 5 canonical record, then `uip df records get`/query it to see `APPROVED`, your email, and a fresh `ReviewedAt`. |
| 7 · Publish | commands below; pack, publish and deploy ran end to end in the 2026-10-02 dry run (participant copy, uip 1.200.1). |

## Pack · publish · deploy

Run from this folder after `uip login`. Participants substitute `ap-approval-review-<user_name>`.

```bash
uip login status --output json                       # must be logged in to customersuccessamer / Training (staging)
npm run build && ls dist/                            # dist/index.html + dist/assets + dist/winner.png

uip codedapp pack dist --dry-run                     # preview only: prints "Package created successfully" but writes nothing
uip codedapp pack dist -n ap-approval-review-<user_name> --version 1.0.0
#   Pack keeps the shared clientId from uipath.json. Output: .uipath/ap-approval-review-<user_name>.1.0.0.nupkg (gitignored)

uip codedapp publish -n ap-approval-review-<user_name> --version 1.0.0 -t Web
#   Uploads the .nupkg and registers the app; writes .uipath/app.config.json.

uip or folders list --output json                    # resolve APAutomation_<user_name> -> Key (GUID); needs @uipath/orchestrator-tool
uip codedapp deploy -n ap-approval-review-<user_name> --folder-key <APAutomation_<user_name> Key> < /dev/null
#   Always pass --folder-key; the interactive picker fails in non-TTY shells. Re-publish needs a version bump:
#   after any change following a deploy, bump the version and pack / publish / deploy again.
```

The deployed URL is `https://<org>.staging.uipath.host/<slug>` and is already in the AppSDK redirect list on
Training. `dist/index.html` carries the localhost meta tags from the dev build; the platform replaces them at
deploy (redirect URI, api base URL, tenant, folder key).

## Design notes (why it is built this way)

- **One read path.** `queryRecordsById` is followed cursor-by-cursor (`hasNextPage` / `nextCursor`, never
  incremented) until every row is loaded; KPIs, coverage, search, sort and table pagination are derived from
  those rows, so the four cards are "derived from loaded data, not separate calls" and always agree with the
  table. A participant entity has tens of rows. The loop is capped (`fetchPageSize 100 × maxFetchPages 50`) and
  the UI says so if the cap is hit. Beyond that scale, move search to a server-side `filterGroup`
  (`Contains` on `VendorName` / `InvoiceNumber`) and KPIs to `aggregates` + `totalCount`.
- **`ApprovalPackageJson` is re-read by id when the panel opens.** List/query reads of the `MULTILINE_TEXT`
  field (what Lab 5 creates) can return a size marker (`HasValue=true Length=N …`), not content; `getRecordById` returns the full value.
  The reject path never echoes that marker back (it would destroy the stored package) — if the full value cannot
  be read the decision is still saved and the UI says the note was not appended.
- **No client-side router.** Two screens are plain component state, which also avoids the deployed-app
  base-path pitfall (`base: './'` + `getAppBase()` only matter once you add a router).
- **Signed-in email** comes from `ConversationalAgent.user.getSettings()` (same call the lab tracker uses,
  covered by `OR.Users.Read`). If it returns no email the app still shows the worklist but disables
  Approve/Reject and says why — `ReviewedBy` must be the reviewer's email.
- **Error taxonomy** (`src/data/errors.ts`): 401 → auth (sign in again), 403 → scope/permission hint,
  404 → entity-id / folder-key hint, everything else → service error with retry.

## What could not be verified offline (facilitator checklist)

Verified on this machine: `npm install`, `npm run type-check`, `npm run build` (relative asset paths in
`dist/index.html`), the dev server boots with the meta tags injected from `uipath.json`, the sign-in screen
renders without console errors, and the sign-in button redirects to the staging identity server with the
configured client id, `redirect_uri=http://localhost:5173` and the configured scopes.

Not verified (needs a signed-in session on the staging tenant and a populated entity):

1. **The full OAuth round-trip** (`completeOAuth`) and that `user.getSettings()` returns an email for every
   participant account. If it does not, the profile warning shows and decisions are disabled — check the
   scope on the shared client.
2. **Live reads/writes against `AP_Invoice_<user_name>`**: `getById` schema discovery, the cursor loop,
   `updateRecordById` payload shape (Text / DateTime fields; `ReviewedAt` is written as an ISO string, which
   matches how the lab tracker writes `AcknowledgedAt`), and whether `sortOptions` on the `UpdateTime` audit
   column is accepted (if the server rejects it, drop `sortOptions` in `useInvoices.ts`; sorting is redone
   client-side anyway).
3. **`ApprovalPackageJson` is `MULTILINE_TEXT`**, which is what Lab 5 creates. The panel also handles the
   marker/refetch path.
4. **Screens 1 and 2 rendered with real data** — the layout was reviewed from code and the build only.
5. **Pack / publish / deploy** of this reference folder itself. The same commands ran end to end on a
   participant copy in the 2026-10-02 dry run. `.uipath/project.json` follows the lab tracker's;
   `uip codedapp pack` will add `metadata.json` / `app.config.json` next to it.

## SDK and toolchain notes from the dry run

- `entities.updateRecordById` (used here) is deprecated in SDK 1.7.2. Today's participant apps address the
  entity by name: `entities.getByName`, `getRecordsByName`, `getRecordByName` and
  `entities.updateRecord({ name }, id, patch)`, which needs no entity-id placeholder.
- `package.json` pins React 18, Vite 5, TypeScript 5.4 and SDK ^1.5.3. Today's create-vite scaffold produces
  React 19, Vite 8, TypeScript 6 and SDK 1.7.2. The code still builds; expect version differences when you
  compare.
- `uipath.json` `baseUrl` stays the plain host (`https://staging.uipath.com`) even though the coded-apps skill
  says to use the api subdomain; the deployed app gets the api host injected.
