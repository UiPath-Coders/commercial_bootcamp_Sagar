# Lab 1 – IXP Vendor Invoice Model

## Project

| | |
|---|---|
| Project title | Vendor Invoice Sagar |
| Project name | `vendor-invoice-sagar-4113ba41-ixp` |
| Environment | staging.uipath.com · org `customersuccessamer` · tenant `Training` |
| Live version | 6 (tag `live`, published 2026-10-01 19:48 UTC; trained 2026-10-01 19:35 UTC) |
| Documents | 5 (`commercial-invoice-006` … `010`), all reviewed and confirmed |
| Validation metrics | Not yet available — IXP had not validated version 6 at publish time |

## Field group: Vendor Invoice

> Extract the vendor identity and tax registration, invoice and purchase-order references, total payable amount, currency, and dates needed to match and approve a vendor invoice.

| # | Field | Type | Instructions |
|---|---|---|---|
| 1 | Vendor Name | Exact Text | Extract the supplier's full legal name exactly as shown in the vendor, supplier, from, remit-to, letterhead, or supplier-of-record area. |
| 2 | Vendor Tax ID | Exact Text | Extract the vendor's US EIN in NN-NNNNNNN format. Preserve leading zeros; do not capture a phone or account number. |
| 3 | Invoice Number | Exact Text | Extract the invoice or document number, including prefixes and punctuation. |
| 4 | Invoice Date | Date | Extract the invoice issue date only, not the purchase-order, ship, or service date. Normalize it to MM/DD/YYYY. |
| 5 | PO Number | Exact Text | Extract the complete purchase-order reference, including its prefix and leading zeros. Watch for OCR confusion between O and 0. |
| 6 | Total Amount | Number | Extract the final grand total payable for the whole invoice, after sales tax/VAT, freight and other charges and after discounts. It is normally the last, bold or highlighted figure at the bottom of the totals block, labelled TOTAL, TOTAL DUE, TOTAL (USD), Grand Total, Invoice Total or Balance Due. Check that it equals Subtotal plus tax and charges. Never return the Subtotal, Net or pre-tax amount, a tax line, or a line-item amount. If an 'Amount Due' or 'Balance Due' figure differs from the grand total (for example because of a deposit or prior payment), return the grand total including tax. Return the number only, without currency symbol or thousands separators. |
| 7 | Currency | Exact Text | Extract the three-letter currency code. When only a dollar sign is present, return USD. |
| 8 | Due Date | Date | Extract the payment due date, or derive it from the invoice date and explicit payment terms. Normalize it to MM/DD/YYYY. |

## Live model vs. `reference/expected-extractions.json`

Predictions from live version 6, compared field by field. Dates and Total Amount are compared in IXP's normalized form (`ixp_normalized` in the reference file); all other fields against `expected`.

| Invoice | Vendor Name | Vendor Tax ID | Invoice Number | Invoice Date | PO Number | Total Amount | Currency | Due Date |
|---|---|---|---|---|---|---|---|---|
| 006 Great Lakes Steel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 007 Liberty Print | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 008 Summit Facilities | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 009 Vertex Analytics | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 010 Pacific Timber | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Result: 40 / 40 fields match.**

Note: these five documents are also the project's confirmed training labels, so this is an in-sample check, not an independent test.
