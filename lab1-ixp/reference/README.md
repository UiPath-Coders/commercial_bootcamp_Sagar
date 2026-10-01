# Lab 1 reference — Vendor Invoice IXP project

Facilitator-only reference for **Lab 1 — IXP / Document Understanding** of the UiPath Commercial Bootcamp
(Office of the CFO, Invoice-to-Pay, process step *Extract Invoice Data*). Lab 1 has no code deliverable: a participant
pastes prompts into Claude Code and the `uipath-ixp` skill creates the project in the tenant. This folder holds the
concrete artifacts needed to verify that what landed in the tenant is right.

Nothing here is used by participants during the lab; keep it out of the prompts.

## Contents

| File | What it is |
|---|---|
| `taxonomy.json` | The `Vendor Invoice` document type: one field group, 8 fields (name, type, instructions copied from `../fields-to-extract.md`), the overall project prompt, the recommended model config, and the step-4 Total Amount fix. Format: a mirror of the `uip ixp groups add` / `fields add` / `projects update-prompt` parameters (see *Taxonomy format* below). |
| `payloads/groups-add-fields.json` | The exact JSON array to pass as `--fields` to `uip ixp groups add`. |
| `payloads/fields-update-prompts-total-amount.json` | The exact `--updates` payload for `uip ixp fields update-prompts` that fixes Total Amount in lab step 4. |
| `expected-extractions.json` | Ground truth for all 10 packets (001–005 in `lab2-rpa/`, 006–010 in `lab1-ixp/`): file, lab folder, layout, the 8 expected values as printed, the IXP-normalized forms (`Date`, `Number`, `Monetary Quantity`), the on-page label for each field, and the distractor values (subtotal, tax, terms). |
| `expected-extractions.csv` | Flat version of the same, one row per invoice. |
| `annotation-guide.md` | Which label carries each field on the classic / banded / service layouts, what to confirm vs leave unannotated, and how to score a participant's model. |

## How the ground truth was produced

`../../generate_invoices.py` is the single source: its `INVOICES` list holds every header value and `computed()` derives
subtotal, tax and total. `expected-extractions.json` was generated from that module (reportlab stubbed) and every value
was then cross-checked against `pdftotext -layout` of the rendered PDF: each of the 7 text/date fields must appear
verbatim in the page text, and the total must appear on the layout's total line (`TOTAL DUE` for classic,
`BALANCE DUE` for banded, `TOTAL (USD)` for service) as `$x,xxx.xx USD`. All 10 passed. Regenerate with the same check if
`generate_invoices.py` changes.

## Taxonomy format

The `uipath-ixp` skill (`uip ixp projects import-taxonomy`) accepts two file shapes — `{ field_types, label_group }` and
`{ entity_defs, label_groups }` — but its reference documents them only by top-level key and a few nested names
(`label_defs`, `moon_form`, `field_id`, `field_type_id`, `instructions`), not a full schema. Rather than guess,
`taxonomy.json` mirrors the documented CLI parameters the lab actually uses, and the `payloads/` files are the literal
arguments. To obtain a real import file, export it from any correctly built participant project:

```bash
uip ixp projects get-taxonomy <project-name> --output json | jq .Data.dataset > vendor-invoice.import.json
```

`import-taxonomy` reads `entity_defs` / `label_groups` at the top level, so pass the inner `dataset` object.

Type note: `fields-to-extract.md` types Total Amount as `Number`; the skill's Critical Rule 17 steers Claude Code to the
built-in `Monetary Quantity` for currency amounts. Both are acceptable and both appear in `expected-extractions.json`
(`ixp_normalized`).

## Verifying a participant's project (documented, not run here)

Requires a `uip login` to the bootcamp tenant (`customersuccessamer` / `Training` on staging). All commands are read-only.
Use the project **Name** (slug with UUID and `-ixp` suffix), never the Title.

```bash
# 1. Find the participant's project (Title is "Vendor Invoice <first name>")
uip ixp projects list -l 200 --output json          # Data.Projects[] -> { Id, Name, Title, CreatedAt }

# 2. Documents: expect Total = 5, Filenames = commercial-invoice-006..010
uip ixp documents list <project-name> --output json

# 3. Taxonomy: expect one label group "Vendor Invoice" with 8 fields; types under entity_defs
uip ixp projects get-taxonomy <project-name> --output json
#    -> Data.dataset.label_groups[].label_defs[] (fields with name / field_type_id / instructions)
#    -> Data.dataset.entity_defs[] (data types; match field_type_id -> name)
#    -> Data.dataset._model_config (model_version, input_config) if you want to check configure-model

# 4. Predictions for all 5 documents: compare FormattedValue to expected-extractions.json
uip ixp labellings get-predictions <project-name> --output json
#    -> Data.Predictions[] { DocumentId, Labels[] { Name, Occurrence, Fields[] { FieldId, FieldName, FormattedValue } } }

# 5. Model versions and tags: expect a `live` tag after the deploy step
uip ixp projects list-models <project-name> --output json

# 6. Metrics for the published version (F1 is agreement with confirmed labels, not truth — see annotation-guide.md)
uip ixp projects get-metrics <project-name> --output json
uip ixp projects get-metrics <project-name> --model-version <N> --output json

# 7. Taxonomy as it was when version N was trained (to check the step-4 Total Amount instruction landed)
uip ixp deployments get-taxonomy <project-name> --version <N> --output json
```

Scoring rules and the layout-by-layout label map are in `annotation-guide.md`.

## Rebuilding a reference project yourself (optional, mutating)

If you need a golden project in the tenant, this is the documented path (`payloads/` supply the arguments):

```bash
cd commercial_bootcamp_lab_assets/lab1-ixp
uip ixp projects create "Vendor Invoice Reference" . --skip-taxonomy --output json      # note ProjectName
uip ixp projects configure-model <project-name> --model gemini_2_5_flash --preprocessing table_mini --output json
uip ixp groups add <project-name> --name "Vendor Invoice" \
  --instructions "$(jq -r '.field_groups[0].instructions' reference/taxonomy.json)" \
  --fields "$(cat reference/payloads/groups-add-fields.json)" --output json
uip ixp projects update-prompt <project-name> \
  --prompt "$(jq -r '.project.overall_extraction_instructions' reference/taxonomy.json)" --output json
# ... review/confirm per annotation-guide.md, then:
uip ixp fields update-prompts <project-name> --updates "$(cat reference/payloads/fields-update-prompts-total-amount.json)" --output json
uip ixp projects publish <project-name> --tag live --description "Lab 1 reference" --output json
```

Do not run these against a participant's project.
