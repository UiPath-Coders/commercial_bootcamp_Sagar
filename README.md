# Commercial Bootcamp lab assets

**A cloneable, local-first workspace for the UiPath Commercial Bootcamp**

Clone this repository and you have the complete working set for Labs 1–7 and the Lab 10 reference:

- the synthetic invoices, emails, fixtures, and design inputs participants start from;
- a real local mock ERP with both an API and browser portal;
- the prompts and contracts each coding agent must follow;
- finished reference implementations under each lab's `reference/` folder.

The repository is meant to work as both a workshop and an answer book. Participants build in their own copy,
then compare their result with the reference—without editing the golden repository.

> All vendors, tax IDs, purchase orders, invoices, and amounts are synthetic.

## Start here

You need Git, Node.js, Python with `uv`, and the UiPath CLI for all validations. The individual lab READMEs
tell you which subset is needed.

Start the included ERP locally:

```bash
cd mock-erp
node smoke.mjs
node server.mjs
```

Then open [http://localhost:8080/portal/](http://localhost:8080/portal/). Lab 3 calls its PO API at
`http://localhost:8080`; Lab 4 drives the portal at `http://localhost:8080/portal/`.

## What is here

| Folder | Lab | Participant builds | Included answer |
|---|---:|---|---|
| `lab1-ixp/` | 1 | an invoice extraction model | expected values for all ten invoices, taxonomy, and annotation guide |
| `lab2-rpa/` | 2 | an extraction agent and intake RPA process | validated low-code agent plus a compiling cross-platform XAML project |
| `lab3-api/` | 3 | Python Functions for PO matching, per-record processing, queue processing, and status reads | function project with four entry points and 107 tests against the mock ERP |
| `lab4-rpa/` | 4 | browser RPA that posts an invoice | compiling cross-platform XAML project using the real mock portal selectors |
| `lab5-coded-agent/` | 5 | a LangGraph approval-package agent | coded agent with 70 tests and a six-case offline evaluation |
| `lab6-coded-app/` | 6 | an AP reviewer Coded App | React/TypeScript app that type-checks, builds, and packs |
| `lab7-planner/` | 7 | a PDD and SDD for the assembled process | source process and human-readable guidance; no tenant-specific answer by design |
| `lab8-platform/` | 8 | a read-only inspection report of their folder | README with the report contents and redaction list |
| `lab9-governance/` | 9 | a tool-use policy draft and access notes | README listing the five Lab 9 steps |
| `lab10-maestro-bpmn/` | 10 | the Maestro BPMN process that orchestrates Labs 2–6 | the BPMN solution from the dry run (both paths reached Paid), with tenant keys replaced by placeholders |
| `challenge-maestro-flow/` | homework | the same process as a Maestro Flow, on their own | invoice 011 and the brief; no answer until after the presentation session |
| `mock-erp/` | 3–4 | nothing—it is the system being automated | zero-dependency API and AP portal, Dockerfile, and smoke suite |
| `CLAUDE.md` | all | nothing—it is read by Claude Code | the tenant facts, CLI traps and per-lab runtime rules every lab session needs |

## Repo layout

Every lab folder from 1 to 7 has a `reference/README.md`. In `lab7-planner/` it explains why there is no
tenant-specific answer. Labs 8 and 9 operate on the participant's tenant; `lab8-platform/` and
`lab9-governance/` hold only a README, and each lab writes its files there in the participant's copy. `lab10-maestro-bpmn/` holds the lab README and
`reference/InvoiceApprovalSolution_Reference/`.

## What is local, and what needs a UiPath tenant?

Everything that can be shared safely and reproducibly is in the clone. You can inspect every source file,
serve the mock ERP, exercise its endpoints and portal, run Python tests, build the Coded App, validate the
low-code agent definition, and validate/build both RPA projects locally.

A few values cannot be shipped because they belong to each participant's UiPath tenant:

- the live IXP project/model selected in the Lab 2 agent;
- folder, bucket, queue, process, robot, and Data Fabric resource identities;
- OAuth client and deployed application URLs;
- a public HTTPS URL only when a cloud robot—not the participant's laptop—must reach the mock ERP.

Those are explicit binding steps, never missing assets. The reference projects use `_Reference` names and
offline entity metadata so they compile without pretending to own a participant's cloud resources.

For normal local development, use the included mock ERP at `localhost:8080`. A facilitator-hosted copy is
optional. It is needed only for Automation Cloud execution where `localhost` points at the cloud worker,
not the participant's machine.

## Participant workflow

Environment Setup creates a private copy named `commercial_bootcamp_<user_name>`. Every lab follows the same
rhythm:

1. Open that private copy and paste the lab's prompt from the bootcamp site.
2. Let the coding agent inspect the lab folder and build the named project there.
3. Run the lab's local checks and, where required, bind and run it in the participant's tenant.
4. Compare the result with the lab's `reference/` implementation.
5. Commit and push the participant's work.

Do not initialize nested Git repositories inside lab folders.

## Updating your copy

Your repository is a copy of this one without shared history and without an upstream remote, so never
`git pull` from the golden repo: it refuses unrelated histories or conflicts on every file. Update it with the
"Refresh your copy" prompt (Day 2 Step 0) on the bootcamp site. It clones this repository to a temporary
folder, copies every file except `.git` over your copy without deleting anything of yours, commits the result as
"Sync with golden repo", and also copies `CLAUDE.md` to the root of your `commercial-bootcamp/` workspace folder,
which is the copy every lab session loads. Run it at the start of Day 2, before Lab 5.

## Validate the references

Run the mock ERP first in another terminal:

```bash
cd mock-erp
node smoke.mjs
node server.mjs
```

Then run the checks you need:

```bash
# Lab 2 — low-code extraction agent
cd lab2-rpa/reference/Invoice_Extraction_Agent_Reference
uip agent refresh
uip agent validate
uip agent review

# Lab 2 — invoice intake RPA
cd ../Invoice_Intake_RPA_Reference
uip rpa validate --min-severity warning
uip rpa build

# Lab 3 — Python Functions
cd ../../../lab3-api/reference/POMatch_Reference
uv sync
.venv/bin/python -m pytest -q

# Lab 4 — portal RPA
cd ../../../lab4-rpa/reference/PostToERP_Reference
uip rpa validate --min-severity warning
uip rpa build

# Lab 5 — coded approval agent
cd ../../../lab5-coded-agent/reference/Invoice_Approval_Agent_Reference
uv sync
.venv/bin/python -m pytest -q

# Lab 6 — reviewer app
cd ../../../lab6-coded-app/reference/ap-approval-review
npm install
npm run type-check
npm run build
uip codedapp pack dist --name ap-approval-review --version 1.0.0 --dry-run

# Lab 10 — Maestro BPMN
cd ../../../lab10-maestro-bpmn/reference/InvoiceApprovalSolution_Reference/InvoiceApprovalProcess_Reference
uip maestro bpmn validate InvoiceApprovalProcess_Reference.bpmn
```

The RPA analyzer may report that the organization requires an Automation Hub URL. That is a tenant governance
requirement, not a compilation error and not a value this public reference should invent. On a headless macOS
machine, per-file `uip rpa validate` of a UI Automation workflow can false-fail with `Cannot create unknown type
uix:...`; `uip rpa build` is the gate.

Two toolchains are involved: the `uip` CLI (login with `uip login`) and, for Lab 3, the `uipath` Python CLI:
run `uv run uipath auth --staging` inside the project folder; the login is stored in that folder only (`./.env`,
`./.uipath/.auth.json`). Lab 5 runs through `uip codedagent`, which reuses the `uip login` session.

## The invoice story

The ten one-page US invoices rotate through three layouts and arrive both as PDFs and vendor `.eml` messages
with the matching PDF attached. They use USD, US EINs, itemized line items, and `mm/dd/yyyy` dates.

The fixed ERP data deliberately covers every route through the process:

- auto-approved and ready for Lab 4: invoices 001, 003, 007, and 008;
- approval needed: invoices 002, 004, and 009;
- PO mismatch/hold: invoices 005, 006, and 010;
- approval needed, reserved for the homework Challenge: invoice 011 (`challenge-maestro-flow/`, a second
  Contoso Logistics invoice on PO-2026-0447). No lab uses it.

The Data Fabric record ID created in Lab 2 is the canonical invoice identifier used by every later lab.

## Repository relationships

| Repository | Purpose |
|---|---|
| `commercial_bootcamp_lab_assets` | this golden, cloneable asset-and-reference repository |
| `commercial_bootcamp_lab_tracker` | the human-facing bootcamp pages and exact prompts |
| `commercial_bootcamp_manager_dashboard` | facilitator progress dashboard |
| `commercial_bootcamp_<user_name>` | one participant's private working copy |

The bootcamp site's `docs/commercial-process.md` is the canonical business-process description. If a
reference and a prompt ever disagree, fix the mismatch rather than teaching two versions.

## Regenerate the invoices

Facilitators can regenerate every PDF after changing the synthetic invoice definitions:

```bash
python3 -m venv .venv
.venv/bin/pip install reportlab
.venv/bin/python generate_invoices.py .
```

Pass one or more sequence numbers to write only those invoices and leave the others untouched, for example
`.venv/bin/python generate_invoices.py . 011` for the Challenge invoice.

If a purchase order or amount changes, update the mock ERP fixture and expected extraction files in the same
commit.
