# Fields to Extract: Vendor Invoice

This document defines the extraction scope for the `Vendor Invoice` IXP project. The taxonomy is limited to 8 vendor, invoice, purchase-order, and amount fields.

## Field Group

### Vendor Invoice

Extract the vendor identity and tax registration, invoice and purchase-order references, total payable amount, currency, and dates needed to match and approve a vendor invoice.

## Fields

The field group instruction above and the "What to Extract" column are the exact instructions the Lab 1 setup prompt sends (bootcamp-site `LAB1_IXP_SETUP_PROMPT`); `reference/taxonomy.json` and `reference/payloads/groups-add-fields.json` carry the same text.

| Field | Type | What to Extract | Why It Matters | Where to Look |
|---|---|---|---|---|
| Vendor Name | Exact Text | Extract the supplier's full legal name exactly as shown in the vendor, supplier, from, remit-to, letterhead, or supplier-of-record area. | Identifies the vendor the invoice must be matched and paid against. | Vendor, Supplier, From, Remit To, letterhead, or Supplier of Record section. |
| Vendor Tax ID | Exact Text | Extract the vendor's US EIN in NN-NNNNNNN format. Preserve leading zeros; do not capture a phone or account number. | Confirms the vendor's tax registration for compliant payment. | Tax ID, Tax Ref, EIN, VAT, Supplier Tax ID / VAT, or supplier registration section. |
| Invoice Number | Exact Text | Extract the invoice or document number, including prefixes and punctuation. | Uniquely identifies the invoice and guards against duplicate payment. | Invoice No., Invoice #, Document Number, or the invoice header. |
| Invoice Date | Date | Extract the invoice issue date only, not the purchase-order, ship, or service date. Normalize it to MM/DD/YYYY. | Establishes the invoice age and the basis for the due date and terms. | Invoice Date, Date, Issued, or the invoice header. Do not use the order date, ship date, or service date. |
| PO Number | Exact Text | Extract the complete purchase-order reference, including its prefix and leading zeros. Watch for OCR confusion between O and 0. | Drives the three-way match against the purchase order. | Customer PO, PO, PO Reference, Purchase Order, or the procurement section. |
| Total Amount | Number | Extract the final grand total payable including tax, never the subtotal or amount before tax. | Determines the amount to approve and pay, and whether approval is required. | Total Due, Total, Gross Payable, Amount Due, or the totals block. |
| Currency | Exact Text | Extract the three-letter currency code. When only a dollar sign is present, return USD. | Ensures the amount is matched and paid in the correct currency. | Currency, Billing Currency, the currency symbol on the total, or the totals block. |
| Due Date | Date | Extract the payment due date, or derive it from the invoice date and explicit payment terms. Normalize it to MM/DD/YYYY. | Schedules the payment and protects early-payment discounts. | Payment Due By, Net Due Date, Due Date, or derived from the invoice date plus the payment terms. |

## Extraction Guidance

- Keep extraction focused on these 8 fields only.
- Extract values only when they are present and clearly supported by the document.
- For `Total Amount`, extract the grand total that includes tax — not the subtotal or the amount due before tax.
- For `Invoice Date`, use the issue date; do not substitute the order date, ship date, or service date.
- For `PO Number`, capture the full reference including its prefix; watch for OCR confusion between the letter O and the digit 0.
- For `Currency`, prefer the explicit three-letter code; if only a `$` symbol is shown, map it to USD.
- For `Vendor Tax ID`, keep the exact EIN formatting (NN-NNNNNNN).
- Normalize `Invoice Date` and `Due Date` to MM/DD/YYYY when the source uses another date format.

## Expected Outcome

The model should extract a compact invoice summary containing:

- Vendor name and tax ID
- Invoice number and invoice date
- PO number
- Total amount and currency
- Due date
