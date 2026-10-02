# Lab 1 annotation guide — Vendor Invoice (8 fields)

Facilitator reference for reviewing a participant's IXP project against `expected-extractions.json`.
All ten packets are one-page, digitally rendered PDFs (no scan noise), so OCR garble should be rare;
almost every wrong prediction is a *wrong-source* error, not a character error.

## 1. Three layouts, one label map

`generate_invoices.py` rotates three layouts by sequence number: `(seq - 1) % 3` -> classic, banded, service.

| Field | Classic (001, 004, 007, 010) | Banded (002, 005, 008) | Service (003, 006, 009) |
|---|---|---|---|
| Vendor Name | Letterhead, top-left, 17 pt bold | White text on the navy band, top-left | Centered title, top of page (also repeated in the remittance stub) |
| Vendor Tax ID | `Federal Tax ID (EIN):` under the letterhead | `Vendor EIN` in the right-hand meta grid | `Tax ID:` in the right-hand boxed meta table |
| Invoice Number | `Invoice #` in the rounded meta box, top-right | `No.` in orange under INVOICE on the band | `Invoice Number:` in the meta table (also `Invoice #` in the stub) |
| Invoice Date | `Invoice Date` in the meta box | `Invoice Date` in the meta grid | `Invoice Date:` in the meta table |
| PO Number | `PO Number` in the meta box | `PO Number` in the meta grid | `Customer PO:` in the meta table (also `Customer PO` in the stub) |
| Total Amount | `TOTAL DUE` — last row of the shaded totals block, bottom-right | `BALANCE DUE` — last row of the navy totals block (the same value also appears as `AMOUNT DUE` in the meta grid) | `TOTAL (USD)` — last row of the totals block (same value also as `Amount Due` in the stub) |
| Currency | `Currency` row in the meta box, and the `USD` suffix on TOTAL DUE | No `Currency` label — only the `USD` suffix on AMOUNT DUE / BALANCE DUE and the note "All amounts in USD" | `Currency:` row in the meta table, and the `USD` suffix on TOTAL (USD) |
| Due Date | `Due Date` in the meta box | `Due Date` in the meta grid | `Payment Due:` in the meta table (also `Due Date` in the stub) |

Distractors on every layout: `Subtotal`, `Sales Tax (n%)`, line-item `AMOUNT` / `LINE TOTAL`, `Terms` / `Payment Terms` (Net 15/30/45),
`BILL TO` / `SHIP TO` (Globex Manufacturing — never the vendor), bank routing/account numbers, and the vendor phone number.

## 2. Field-by-field: what to annotate

Follow the skill's verdicts (CONFIRMED / CORRECTED / MISSING / NOT CONFIRMED). Confirm at field level with
`uip ixp labellings confirm <project-name> <document-id> --fields <ids>`; never confirm a wrong value.

| Field | Confirm when the prediction is | Do NOT confirm when |
|---|---|---|
| Vendor Name | The full vendor string incl. suffix (`Inc.`, `LLC`, `Corp.`, `Co.`, `Company`, `Group`) | `Globex Manufacturing ...` (bill-to), the bank name, or a truncated name |
| Vendor Tax ID | The `NN-NNNNNNN` EIN | A phone number, routing `000000000`, or the masked account |
| Invoice Number | Full prefixed number (`GLS-2026-0442`, `AF19427`, `MCS-Q1-20418`) | The PO number, or the number with prefix stripped |
| Invoice Date | Normalized `YYYY-MM-DDT00:00:00Z` of the printed MM/DD/YYYY | The due date (both sit in the same meta block) |
| PO Number | `PO-2026-NNNN` with prefix | Invoice number, or `PO Box 5591` from the bill-to address |
| Total Amount | Grand total incl. tax (the TOTAL DUE / BALANCE DUE / TOTAL (USD) row). `Number` type reads back bare (`17988.20`); `Monetary Quantity` reads back `17988.20 USD` | The Subtotal, the Sales Tax, or a line-item amount. The planted Lab 1 defect. The current model (gemini_2_5_flash + table_mini) often extracts the grand total correctly on all five before step 4; a perfect Total Amount is not suspicious |
| Currency | `USD` | Empty on banded invoices is *not* MISSING — the code is printed as the suffix of AMOUNT DUE / BALANCE DUE and in "All amounts in USD" |
| Due Date | Normalized form of the printed due date | The invoice date, or a date computed from Terms that does not match the printed one |

Notes that change a verdict:

- **Type normalization is not an error.** A `Date` prediction of `2026-03-05T00:00:00Z` for page `03/05/2026`, or a
  `Monetary Quantity` of `17988.20 USD` for page `$17,988.20 USD`, is CONFIRMED as-is. Never use `--corrections` to restore
  the page format (cli-reference.md, Normalized output formats; Critical Rule 8).
- **Subtotal == Total on 002, 004 and 009** (0% sales tax). On those three a Total Amount prediction equal to the Subtotal is
  numerically correct and must be confirmed; the Subtotal-vs-Total defect can only be observed on the other seven
  (in Lab 1's five packets: 006, 007, 008, 010).
- **Amount Due equals the grand total** on banded and service layouts, so a model that reads `AMOUNT DUE` is still right.
- **Nothing is genuinely missing.** All 8 fields are printed on all 10 packets, so `mark-missing` should never be needed in Lab 1.
  A participant who marked a field missing has annotated incorrectly.
- **`--corrections` is OCR-only.** With digital PDFs the only plausible case is an O/0 swap in a PO number
  (`PO-2O26-...`); a wrong-source pick (Subtotal, Invoice Date as Due Date) must be left unannotated and fixed via the prompt.

## 3. Scoring a participant's model

1. Pull the project's taxonomy and predictions (documented in `README.md`):
   `uip ixp projects get-taxonomy <project-name> --output json` and
   `uip ixp labellings get-predictions <project-name> --output json`.
   Map `DocumentId` to a packet via `uip ixp documents list <project-name> --output json` (`Filename` column), then look
   the packet up by `file` in `expected-extractions.json`.
2. For each of the 5 Lab 1 packets (006–010) compare the 8 `FormattedValue`s to `expected-extractions.json`:
   - `Vendor Name`, `Vendor Tax ID`, `Invoice Number`, `PO Number`, `Currency`: exact string match against `expected`
     (case-insensitive, whitespace-trimmed is fine).
   - `Invoice Date`, `Due Date`: match against `ixp_normalized` (`YYYY-MM-DDT00:00:00Z`). Also accept the printed
     `MM/DD/YYYY` if the participant typed a field as Exact Text.
   - `Total Amount`: numeric match against `expected["Total Amount"]` after stripping `$`, `,` and a trailing currency
     code (`17988.20` == `17988.20 USD` == `17,988.20`). A value equal to `distractors.subtotal` is the planted defect.
3. Score = correct fields / 40 (5 packets x 8 fields). Suggested pass marks after step 4 of the lab:
   - **Pass:** 40/40, or 39/40 with a single non-Total-Amount slip explained in the transcript.
   - **Total Amount check:** all five Total Amounts must equal the grand total (`expected`), none the subtotal.
   - **Taxonomy check:** exactly one field group named `Vendor Invoice` with exactly the 8 field names in `taxonomy.json`
     (types: 5 x Exact Text, 2 x Date, Total Amount as Number *or* Monetary Quantity).
   - **Publish check:** `uip ixp projects list-models <project-name> --output json` shows a `live` tag in `Tags[]`.
4. `uip ixp projects get-metrics` F1 is *not* a substitute for this comparison: F1 measures agreement between predictions
   and whatever the participant confirmed, so blind-confirmed wrong values score 1.00 (Critical Rule 15).
