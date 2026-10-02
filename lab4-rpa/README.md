# Lab 4 — post an approved invoice through a browser

Lab 4 automates the final Day 1 step: take one auto-approved invoice from Data Fabric, enter it into an AP
portal, submit it for payment, and mark the same record as posted.

Yes, the portal is real and included in this repository. It is not a screenshot or a future hosting
dependency.

## Run the portal on your laptop

From the repository root:

```bash
cd mock-erp
node smoke.mjs
node server.mjs
```

That local copy is for reading the code and the element ids. For Lab 4 itself, explore and test against the
**hosted** portal (the Portal URL on the bootcamp page, sign in as ap_user / passwod). It contains all ten
bootcamp vendors, validates purchase orders against the shared fixture, records submissions in memory, and
exposes stable element IDs for reliable selectors. Do not point your Lab 4 project at `localhost`: see
"Portable selectors" below for why.

## What you build

Your coding agent creates an unattended, cross-platform RPA project named `PostToERP_<user_name>`.

The process:

1. queries tenant-scoped `AP_Invoice_<user_name>` for the oldest record where `POMatched = true`,
   `ApprovalNeeded = false`, and `PostedToERP` is null or false;
2. reads `InvoiceNumber`, `VendorName`, `PONumber`, and `TotalAmount`;
3. completes the portal's eight-step browser flow in Chrome;
4. verifies the portal confirmation;
5. sets `PostedToERP = true` and `InvoiceLifecycleState = POSTED` on that same record.

It does not read the Lab 2 queue. Lab 3 already consumed those transactions; Data Fabric is the source of
truth.

This is the exact Day 1 selection rule. The later capstone may extend the selection to include
reviewer-approved `InvoiceLifecycleState = APPROVED` records, but that extension is not hidden inside this
reference.

## Portable selectors

Sign in to the hosted portal (the Portal URL on the bootcamp page, ap_user / passwod) in Chrome, then let Claude
Code use the uipath-rpa skill's live UI exploration (snapshot capture, configure-target) against that live page to
find each target. Keeping the Object Repository it builds is fine. Your laptop needs Chrome with the UiPath
extension; grant screen-recording or accessibility permission if macOS asks.

Never explore or test against a localhost copy of the portal in this project. A captured Object Repository screen
stores the URL it was recorded on, and the cloud robot then opens that URL instead of `PortalUrl`; with a localhost
address every selector fails, including the page body. Check before building:

If Claude Code reports that it cannot communicate with the UiPath browser extension (the extension is missing,
disabled in that Chrome profile, or its native-host path is broken), do not let it capture Chrome as a desktop
application: those selectors (`role='AX…'`, window titles with your profile name) build fine and never run on the
serverless robot. Have it build the targets from the element ids in `../mock-erp/README.md` instead; the result
is the same `<webctrl id='…' tag='…' />` selectors. Check before building:

```bash
grep -rl localhost . --exclude-dir=.local        # must return nothing (.objects included)
grep -c "role='AX" PostInvoiceInPortal.xaml       # must print 0
```

The targets run on the cross-platform serverless robot, so:

- Element selectors use only the stable `id` (plus `tag`): no `idx`, positions, visible text, css-selector, or
  aaname chains.
- The browser/window selector is `<html app='chrome.exe' title='Globex AP Portal*' />`: no `url` attribute and
  no host.
- The Use Browser URL is bound to the `PortalUrl` argument, with `InteractionMode=Simulate`.

Done means the job against the hosted portal on the serverless robot. If you get stuck, compare (do not copy) with
`reference/PostToERP_Reference/PostInvoiceInPortal.xaml`.

## Start the lab

Work in your private participant repository:

```text
Work inside commercial_bootcamp_<user_name>/lab4-rpa for the rest of this session. List the files you find.
```

Then follow the Lab 4 bootcamp prompts. They contain the exact project name, entity rule, and deployment
steps.

## The browser path

| # | Action | Stable element |
|---:|---|---|
| 1 | Click **Enter vendor invoice** | `#btn-post-invoice` |
| 2 | Enter Vendor Name | `#input-vendor-name` |
| 3 | Click **Search** | `#btn-search` |
| 4 | Select the returned vendor | `#vendor-row-<vendorId>` |
| 5 | Click **Next** | `#btn-next-1` |
| 6 | Enter invoice number, PO number, and total | `#input-invoice-number`, `#input-po-number`, `#input-total-amount` |
| 7 | Click **Next** | `#btn-next-2` |
| 8 | Click **Post voucher & release for payment** | `#btn-submit-payment` |

A successful submission exposes `#confirmation-id` and the text “Submitted for payment” in
`#confirmation-status`.

## What is in this folder

| Path | Purpose |
|---|---|
| `reference/PostToERP_Reference/` | the finished XAML project with the Data Fabric query, portal automation, confirmation check, and write-back |
| `reference/README.md` | workflow map, local checks, and tenant-binding boundary |
| `../mock-erp/` | the actual API and browser portal automated by this lab |

## Quick reference check

Keep the mock ERP running, then in another terminal:

```bash
cd lab4-rpa/reference/PostToERP_Reference
uip rpa validate --min-severity warning
uip rpa build
```

Expected result: build `true`. A tenant policy may add an Automation Hub URL warning, and on a headless
macOS machine per-file `validate` of the UI Automation workflow can false-fail with `Cannot create unknown type
uix:NApplicationCard`; the build is the gate.

Run the finished process as a job on the serverless cloud robot. Local `uip rpa debug start` on a headless
host has no robot Data Service connection and stops at the first entity query with `EntityServiceException`.

The browser path is proven by that serverless job against the hosted portal. To see what the robot does, walk
the hosted portal's screens yourself in Chrome.

## Done means

- the ready-record query implements the three Day 1 conditions exactly;
- no-ready-record exits cleanly without opening the portal;
- the portal receives the four values from the selected record;
- a failed or unconfirmed submission never sets `PostedToERP`;
- a confirmed submission sets `PostedToERP = true` and `InvoiceLifecycleState = POSTED`;
- validation and build pass;
- the participant's project is committed and pushed.

## Common mistakes

- Trying to consume `InvoiceQueue_<user_name>` again.
- Marking a record posted before reading the portal confirmation.
- Using screen coordinates, positions, or visible text in selectors instead of the portal's stable ids.
- Cloud run: the browser opens the hosted URL, then nothing is found, not even the page body, for about 120 s.
  The robot opened the wrong page, not the wrong element: the portal was explored on localhost and `.objects/`
  kept `Url="http://localhost:8080/portal/"`. Run `grep -rl localhost .`, replace the address with the hosted
  URL, rebuild, republish. The element ids do not change.
- Assuming a laptop's `localhost` is reachable from a cloud robot.
- Adding the capstone lifecycle-state extension to the Day 1 implementation.
- Filtering the entity with the designer operators (`Equals true`, `is null`). They compile and then throw at
  runtime; sort, then select the record in a VB LINQ expression.
- Updating the record without `.Id` on the entity object. The update silently targets nothing.
- Forgetting that the hosted portal needs a sign-in (`ap_user` / `passwod`) before Search returns rows.

## Runtime notes from the dry run

- Pin `UiPath.UIAutomation.Activities` 26.10.3. An unpinned install fails with "No versions found".
- Check Default Serverless with `uip or folders runtimes <folder-key>` (expect Serverless Total 1), not
  `uip or machines list --folder-key`, which shows direct assignments only and is empty for the inherited
  machine.
- `RecordId` is one InOut String argument: blank on input means standalone mode, on output it is the resolved
  record. XAML cannot declare an input and an output with the same name.
- The hosted posting counter restarts per session, so two runs can both return `AP-2026-00001`.
