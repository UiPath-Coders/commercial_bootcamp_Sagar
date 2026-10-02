# Lab 3 — Match PO & Check Approval with UiPath Functions (Python)

**What you build:** a Python Coded Function project called `POMatch_<user_name>` with four functions:

- `po_lookup` asks the ERP about one purchase order and applies the two business rules. It is pure: same
  input, same answer, easy to test.
- `process_invoice` reads one invoice record, calls `po_lookup`, and writes **POMatched** and
  **ApprovalNeeded** back to that record. Safe to run twice. Lab 10 calls this one.
- `process_invoice_queue` takes every transaction from `InvoiceQueue_<user_name>`, hands the record it points
  to to `process_invoice`, and marks the transaction Successful (or Failed, and moves on).
- `get_invoice_status` only reads a record's lifecycle fields, so Lab 10 can wait for the reviewer's decision.

Those two booleans are the `Approval needed?` gateway of the process: matched invoices under 10,000 are
auto-approved and go straight to Lab 4; everything else waits for the Day 2 agent and reviewer.

**How you build it:** in the Claude Code desktop app, on your own copy of this repo, paste the prompts from the
Lab 3 page of the bootcamp site. Start with:

```text
Work inside commercial_bootcamp_<user_name>/lab3-api for the rest of this session. List the files you find.
```

## The two rules (memorise these)

| Rule | Definition |
|---|---|
| **PO matched** | the PO exists **and** the vendor is active **and** the invoice total is within 2% of the PO open amount |
| **Approval needed** | **not** PO matched, **or** the invoice total is above 10,000 |

## What is in this folder

| File / folder | What it is | Who uses it |
|---|---|---|
| `samplepolookup.md` | The ERP contract: `GET /health`, `POST /api/po-lookup`, request and response shapes, and how the response maps to the rules. | You and Claude Code, before writing a line of code. |
| `reference/POMatch_Reference/` | **The complete answer.** `main.py` has all four functions; `tests/` has 107 pytest tests that run `po_lookup` against the live mock ERP for all ten purchase orders plus every error path, and the three Data Fabric functions with the UiPath SDK mocked. `uip function init` and `uip function run` outputs are recorded in its README. | You, at the end of the lab, to run the reference tests against your own function. Facilitators, to grade. |
| `reference/README.md` | Which reference tests run against your own `po_lookup` (the three PO-rule files) and which are reference-internal. | You, in the last step of the lab. |
| `../mock-erp/` | The ERP itself. Run `node server.mjs` and use `http://localhost:8080/api/po-lookup` locally. A facilitator-hosted URL is needed only when a cloud runtime must reach it. | Everyone. |

## Try the reference in two minutes

```bash
cd ../mock-erp && node server.mjs &            # the ERP, on http://localhost:8080
cd ../lab3-api/reference/POMatch_Reference
uv sync && .venv/bin/python -m pytest -q       # 107 passed
uip function run po_lookup --input '{"vendor_name":"Vertex Analytics Corp.","po_number":"PO-2026-0405","invoice_total":22700,"currency":"USD"}'
```

The last command prints `po_matched True, approval_required True`: matched, but over the threshold.

## How to know you are done

1. `po_lookup` returns the expected answer for all ten purchase orders (the table in the repo's root README).
   Unknown PO → not matched. Inactive vendor → not matched. Over tolerance → not matched.
2. `process_invoice_queue` ran on `Default Serverless`; every `AP_Invoice_<user_name>` record has
   POMatched and ApprovalNeeded set (none empty) and every queue transaction is Successful. `process_invoice`
   and `get_invoice_status` give the same answer for one record when called directly.
3. The reference PO-rule tests (`test_rules.py`, `test_po_lookup_live.py`, `test_po_lookup_errors.py`) pass
   against **your** `po_lookup`. The queue and process tests are reference-internal and are read, not run.
4. The project is committed to your repository (last step of the lab).

## Common mistakes

- Reading the queue in Lab 4 too. A transaction can be consumed once; Lab 4 reads the record instead.
- Guessing when the ERP answers badly. Any malformed or failed response must produce an error, not a match.
- Hard-coding the ERP URL. It comes from configuration (`ERP_PO_LOOKUP_URL`, the complete URL; paste a signed
  one as is and never print its token).
- Passing the bare folder name. `folder_path` is the full path `Agentic Bootcamp/APAutomation_<user_name>`; the
  bare name makes *Start Transaction* fail with 400 "Folder does not exist or the user does not have access".

## Runtime notes from the dry run

- **Silence httpx INFO logging.** At INFO, httpx logs the full request URL, and a hosted ERP URL carries the
  signed `access_token`. Put `logging.getLogger("httpx").setLevel(logging.WARNING)` at the top of `main.py`.
- **Re-bind processes after a new package version.** After `uip function init` plus
  `uip or processes update-version`, every process is silently bound to the first entry point
  (`po_lookup`). Re-bind each one with `uip or processes update <key> --entry-point <entry point>` and check
  it with a job or `uip or packages entry-points`; `uip or processes get` shows `EntryPointPath ""` even when
  the binding is right.
- **Set the ERP URL on the process for Lab 10.** Maestro cannot pass job environment variables, so also set
  `ERP_PO_LOOKUP_URL` as a process environment variable on `POMatch_<user_name>_process_invoice` (and
  `_process_invoice_queue`) with `uip or processes update <key> --environment-variables "ERP_PO_LOOKUP_URL=<signed url>"`.
  Without it, a call from Maestro falls back to `http://localhost:8080` and returns `ERP_UNREACHABLE`.
- **SDK queue calls and empty bodies.** `create_transaction_item` / `complete_transaction_item` return
  `response.json()`, so an empty 200 or 204 raises `JSONDecodeError` even though the call succeeded. Catch it,
  and never leave a transaction In Progress.
- **Python SDK login is per folder.** Run `uv run uipath auth --staging` inside `POMatch_<user_name>`; it writes
  `./.env` and `./.uipath/.auth.json` (a token), both git-ignored.
- **Only the PO-rule tests run against your code.** See `reference/README.md`.

All vendors, purchase orders and amounts are synthetic.
