# Lab 6 — Review & Approve with a UiPath Coded App

**What you build:** `ap-approval-review-<user_name>`, the human step of the process. An accounts-payable
reviewer signs in, sees a worklist of invoices that need a decision with the Lab 5 agent's package and
recommendation next to each one, and clicks **Approve** or **Reject**. That click is the `Approved?` gateway:
the app writes InvoiceLifecycleState, ReviewedBy and ReviewedAt to the same `AP_Invoice_<user_name>` record,
approved invoices become ready to post for Lab 4, rejected ones end the process.

**How you build it:** in the Claude Code desktop app, on your own copy of this repo, paste the prompts from the
Lab 6 page of the bootcamp site. Start with:

```text
Work inside commercial_bootcamp_<user_name>/lab6-coded-app for the rest of this session. List the files you find.
```

## What the app must do

| Screen | Content |
|---|---|
| **1 · Gate page** | Shown right after sign-in: UiPath sign-in blue theme, cool neutrals, `winner.png` and the text of `message.txt`, one button into the worklist. |
| **2 · Worklist** | Four KPIs (Total Invoices, Approval Needed, Pending Review = NEEDS_AP_REVIEW + READY_FOR_APPROVAL, Recommended for Approval = AgentRecommendation READY_FOR_APPROVAL), search by vendor name and invoice number, pagination (page size 5, so the seeded ~11 records span three pages), an **Approval required** column (amber "Needed" only until a reviewer decides, then a neutral Approved / Rejected / Posted pill), and a detail panel with AgentRecommendation, ApprovalEvidenceState, MissingApprovalFields and ApprovalPackageJson rendered as a readable package (narrative, evidence checklist with missing fields highlighted, PO-match summary, reviewer note, raw JSON behind a collapsed toggle). |
| **Decisions** | Approve and Reject are enabled when InvoiceLifecycleState is READY_FOR_APPROVAL or NEEDS_AP_REVIEW and ApprovalNeeded is true. Approve → APPROVED, Reject → REJECTED. On NEEDS_AP_REVIEW the detail panel shows a one-line note that approval evidence is incomplete (MissingApprovalFields). Both write ReviewedBy (your email) and ReviewedAt (now). Every other state: buttons disabled with the reason. |
| **States** | Loading, empty, partial data, sign-in error and service error each have their own view. |

No mock mode, no embedded tokens, no second data store: the app reads and writes the entity through the
authenticated UiPath TypeScript SDK.

## What is in this folder

| File / folder | What it is | Who uses it |
|---|---|---|
| `message.txt`, `winner.png` | The two inputs for the gate page. | Claude Code, when it builds your app. |
| `reference/README.md` | What the reference decides, how it differs from today's scaffold, and which approval rule it uses. | You, before you compare. |
| `reference/ap-approval-review/` | **The complete answer.** A React + TypeScript + Vite Coded App: `src/auth` (SDK sign-in), `src/data` (typed field names, cursor-paginated entity query, KPI math, the Approve / Reject write), `src/screens` (gate page, worklist), `src/components` (KPI strip, table, detail panel, state views). `npm run build` and `npm run type-check` pass. | You, at the end of the lab, to compare with your app. Facilitators, to grade. |

## Try the reference in two minutes

```bash
cd reference/ap-approval-review
npm install
# To run the reference (not your app): put your AP_Invoice_<user_name> entity id in src/config/uipath.ts (uip df entities list --output json)
npm run dev          # http://localhost:5173, sign in with your @uipath.com account
```

## How to know you are done

1. You sign in, see the gate page, and reach the worklist with the four KPIs computed from **your** entity.
2. Searching a vendor name or invoice number narrows the list; the detail panel shows the Lab 5 fields.
3. Approving the READY_FOR_APPROVAL record writes APPROVED plus your email and a timestamp; Lab 4's ready-to-post
   query now returns it. Rejecting writes REJECTED.
4. `npm run build` passes, the app is packed, published and deployed to `APAutomation_<user_name>` with an
   explicit folder key, and the project (without `node_modules` and `dist`) is committed to your repository.

## Common mistakes

- Reading the entity by a hard-coded field list that does not match the live schema. Discover it first
  (`uip df entities get`), the system names are PascalCase with no spaces.
- A mock data mode "for now". The reference has none, and neither should your app.
- Forgetting to register the deployed app URL on the OAuth client (facilitator step), which makes sign-in
  fail only after deployment. On Training the deployed URL, `https://<org>.staging.uipath.host/<slug>`, is already
  in the AppSDK redirect list.
- Using the api subdomain as `baseUrl` in `uipath.json`. The working value is `https://staging.uipath.com`.
- Deploying without `--folder-key`. The CLI opens an interactive folder picker that hangs inside Claude Code;
  resolve the key with `uip or folders list --limit 200` and pass it with the lowercase package name.
- Approving a row by Record ID. The worklist has no Record ID column: find the row by InvoiceNumber and
  VendorName, approve only that one, and check that no other record changed to APPROVED or REJECTED.

## Runtime notes from the dry run

- `baseUrl` in `uipath.json` stays the plain host even though the coded-apps skill says to use the api
  subdomain; the deployed app gets the api host injected.
- Add `.uipath/` to your app's `.gitignore`. `uip codedapp` writes local state there.
- `uip codedapp pack --dry-run` prints "Package created successfully" but writes nothing.
- After any change that follows a deploy, bump the version, then build, pack, publish and deploy again. The
  dry run left an older build deployed after a later fix.

All data is synthetic.
