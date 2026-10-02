# Lab 3 reference

`POMatch_Reference/` is the complete answer for Lab 3: one Python Coded Function project with the four entry
points `po_lookup`, `process_invoice`, `process_invoice_queue` and `get_invoice_status`. Its own
`POMatch_Reference/README.md` walks through every function, the configuration variables and the recorded
local runs.

## Which tests you can run against your own function

The 107 tests in `POMatch_Reference/tests/` were written for this reference, so most of them import its
internals. Only the PO-rule tests are meant to be pointed at your code.

| File | Kind | What it needs from your `main.py` |
|---|---|---|
| `test_po_lookup_live.py` | PO rules, black-box against the live mock ERP (all ten purchase orders) | `po_lookup`, `POLookupInput`, `erp_api_url()` |
| `test_po_lookup_errors.py` | PO rules, black-box with the HTTP call mocked (malformed, failed and unreachable ERP; URL and token handling) | the above plus `erp_po_lookup_url()`, `redact()`, `DEFAULT_ERP_PO_LOOKUP_URL` and an `_erp_client()` the fixture can swap |
| `test_rules.py` | PO rules, pure (no HTTP, no SDK) | `PO_TOLERANCE`, `APPROVAL_THRESHOLD`, `evaluate_po`, `parse_po_response`, `MalformedErpResponse` |
| `test_process_invoice.py` | reference-internal | the reference's SDK fake, `_process_invoice`, `_complete`, `_get_field` |
| `test_process_invoice_queue.py` | reference-internal | the reference's queue inputs (`entity_id`, `erp_api_token_asset_name`) and `_Reference` defaults |

All three PO-rule files also expect the input model to be named `POLookupInput` and `match_reason` to use
exactly `MATCHED`, `PO_NOT_FOUND`, `VENDOR_INACTIVE` and `OUTSIDE_TOLERANCE`. `test_rules.py` imports the
helper names in the table; if your function keeps the rules inside `po_lookup`, run only the live and error
files.

Copy the three PO-rule files and `conftest.py` into your project's `tests/` folder, keep the mock ERP running
(`node server.mjs` in `../../mock-erp`), and run:

```bash
uv run pytest -q tests/test_po_lookup_live.py tests/test_po_lookup_errors.py tests/test_rules.py
```

Read the two reference-internal files to compare behavior; do not expect them to pass against your code.

## Running the full suite against the reference itself

From `POMatch_Reference/`, with the mock ERP running and no `BOOTCAMP_USER_NAME` or `AP_FOLDER_PATH`
exported (the suite expects the `_Reference` defaults, including the folder path
`Agentic Bootcamp/APAutomation_Reference`):

```bash
uv sync
.venv/bin/python -m pytest -q        # 107 passed
```

## Runtime differences from your copy

- `folder_path` defaults to the full path. The reference resolves to `Agentic Bootcamp/APAutomation_Reference`;
  yours is `Agentic Bootcamp/APAutomation_<user_name>`. The bare folder name returns 400 "Folder does not
  exist or the user does not have access".
- `main.py` sets the httpx logger to WARNING. At INFO it logs the full request URL, including the signed
  `access_token` of a hosted ERP URL.
- Never copy the `_Reference` names into your project.
