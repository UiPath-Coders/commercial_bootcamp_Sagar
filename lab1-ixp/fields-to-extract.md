# Fields to Extract: Vendor Invoice

This document defines the extraction scope for the `Vendor Invoice` IXP project. The taxonomy is limited to 8 vendor, invoice, purchase-order, and amount fields.

## Field Group

### Vendor Invoice

Extract the vendor identity and tax registration, the invoice and purchase-order references, and the total payable amount, currency, and dates needed to match and approve the invoice.

## Fields

| Field | Type | What to Extract | Why It Matters | Where to Look |
|---|---|---|---|---|
| Vendor Name | Exact Text | The supplier's full legal name exactly as shown. | Identifies the vendor the invoice must be matched and paid against. | Vendor, Supplier, From, Remit To, letterhead, or Supplier of Record section. |
| Vendor Tax ID | Exact Text | The vendor's US tax identifier (EIN) formatted NN-NNNNNNN. Preserve all characters and leading zeros. | Confirms the vendor's tax registration for compliant payment. | Tax ID, Tax Ref, EIN, VAT, Supplier Tax ID / VAT, or supplier registration section. |
| Invoice Number | Exact Text | The vendor's invoice or document number, including any prefix and punctuation. | Uniquely identifies the invoice and guards against duplicate payment. | Invoice No., Invoice #, Document Number, or the invoice header. |
| Invoice Date | Date | The date the invoice was issued. | Establishes the invoice age and the basis for the due date and terms. | Invoice Date, Date, Issued, or the invoice header. Do not use the order date, ship date, or service date. |
| PO Number | Exact Text | The purchase-order reference the invoice bills against, including its prefix. Preserve all digits and leading zeros. | Drives the three-way match against the purchase order. | Customer PO, PO, PO Reference, Purchase Order, or the procurement section. |
| Total Amount | Number | The grand total payable, including tax. Extract the final total, not the subtotal or amount before tax. | Determines the amount to approve and pay, and whether approval is required. | Total Due, Total, Gross Payable, Amount Due, or the totals block. |
| Currency | Exact Text | The three-letter currency code (USD on every packet), or the currency implied by the invoice's currency symbol. | Ensures the amount is matched and paid in the correct currency. | Currency, Billing Currency, the currency symbol on the total, or the totals block. |
| Due Date | Date | The date payment is due. | Schedules the payment and protects early-payment discounts. | Payment Due By, Net Due Date, Due Date, or derived from the invoice date plus the payment terms. |

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
