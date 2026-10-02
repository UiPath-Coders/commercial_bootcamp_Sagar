# Lab 7 reference: why there is no answer file

Every Lab 7 document is written from **your** tenant. The PDD comes from the business prompt, but the gap
analysis reads what `Agentic Bootcamp/APAutomation_<user_name>` actually contains, and the SDDs and task graph
are derived from that gap analysis. Two participants who both finished Labs 1-6 still have different resource
names, keys, versions and states, so a shipped answer would be wrong for everyone except its author. This folder
therefore holds no PDD, SDD or task file.

## Compare against these instead

- **The process.** The bootcamp site's Home page diagram and the "What you build in this lab" section of every
  lab: six steps, three gateways (`Valid?`, `Approval needed?`, `Approved?`), two Rejected ends, one Paid end.
- **The rules.** `../source-process.md` and the Lab 7 PDD prompt: the 2% tolerance, the 10,000 USD threshold,
  structural validity, and the ready-to-post rule.
- **The file set.** The table in `../README.md`: the PDD with its gap section, `invoice-approval-solution-sdd.md`,
  one `*-sdd.md` per RPA process, agent, coded app and BPMN process, `Invoice Approval Solution SDD.docx`, and
  `implementation-tasks.md`.
- **Your own tenant.** Every resource the gap analysis names must exist in your folder.

## What a correct gap table looks like

Mark a step "implemented and verified" only when your tenant shows the evidence. Before anyone has approved or
rejected an invoice in the Lab 6 app, steps 5 and 6 are "partial": the app and the posting robot exist, but no
reviewer decision has gone through them yet. The dry run reported exactly that, and it was correct. The end-to-end
Maestro orchestration stays "target-state only" until Lab 10.
