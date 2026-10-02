# Homework challenge: the invoice process as a Maestro Flow

One week · TAMs · optional for CSMs

Lab 10 gave you the end-to-end invoice process as executable BPMN, with every prompt written for you. This week
you build the same business process again as a UiPath Maestro Flow, on your own. No prompts, no support. Next week
we meet and each of you walks us through how you did it.

## Goal

Intake, PO match, approval decision, human review, post to ERP, and the Paid, Held, Rejected and Invalid outcomes,
implemented as a `.flow` project in its own solution. It calls your published Lab 2 to 6 resources in
`APAutomation_<user_name>`. Do not change them and do not touch your working BPMN solution.

## Definition of done

1. The Flow validates and deploys from its own solution, independent of the BPMN project.
2. An auto-approved invoice reaches Paid with one unchanged RecordId.
3. Invoice 011 waits for your approval in `ap-approval-review-<user_name>`, resumes, and reaches Paid with one
   unchanged RecordId.
4. Any wait for a human gives up after about 15 minutes and ends the instance in a clear state.

## Pointers, not steps

- Build it with whatever suits you: the Claude Code desktop app as in the labs, the Claude Code terminal, or VS Code
  with the UiPath Maestro extension if you want to watch the canvas while you work. The `uipath-maestro-flow` skill
  is installed either way.
- Your resources are already published and the registry knows their contracts. Check which invoices are still
  unused in your entity before you pick one. 006 and 010 are holds by design.
- Your signed ERP URL expires. Mint a new one in Lab 3 before your runs.
- Deploying a solution creates a new child folder every time. Name it so you can find it.
- Stuck for more than an hour on one thing? Post in the bootcamp channel. That is a finding, not a failure.

## Invoice 011 is reserved for your reviewer-path run

This folder holds one invoice that no lab uses:

| File | What it is |
|---|---|
| `commercial-invoice-011-contoso-logistics.pdf` | Contoso Logistics LLC, invoice CLL-2026-3418 on PO-2026-0447, 12,720.00 USD. It matches its PO and is over the 10,000 USD threshold, so it needs your approval. |
| `emails/commercial-invoice-011-contoso-logistics.eml` | The same invoice as the vendor's email to Accounts Payable, PDF attached. |

Keep it for the run where you approve the invoice yourself. Put it into your inbox only when your Flow is ready
for that run.

## Bring next week

- How long it took, build versus runs
- How you approached it and what you asked first
- Where you got stuck and how you got past it
- BPMN versus Flow: what you would change

## Checkpoints

1. Flow validated and deployed from its own solution
2. Both runs reached Paid: one auto-approved, one after my approval of invoice 011
3. Presented my approach, timing and challenges in the follow-up session

The challenge is tracked separately and never counts toward your lab completion.

There is no answer in this folder. A `reference/` folder will be added after the presentation session.
