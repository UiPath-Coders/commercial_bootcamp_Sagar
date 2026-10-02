# Vendor Invoice Approval — Source Process

Every finance team pays vendor invoices. Invoices arrive by email and as PDF attachments,
and before an invoice can be paid someone has to check it is complete, confirm it bills
against a real purchase order for the right amount, obtain approval when policy requires
it, and post it to the ERP so payment can be scheduled. Today this process is largely
manual — keying invoice data, chasing approvers, reconciling three-way matches by hand.
It takes days, misses early-payment discounts, and occasionally pays the same invoice
twice.

## Process steps

1. **Extract Invoice Data** — A vendor invoice arrives. The vendor name and tax ID, the
   invoice number and date, the purchase-order number, the total amount, the currency,
   and the due date are read from the document.
2. **Validate & Create Record** — The extracted invoice is checked for structural
   completeness. An invoice with no purchase-order number or no total amount is rejected
   and returned to the vendor. A complete invoice becomes one invoice record that every
   later step reads and updates; nothing downstream creates a second copy.
3. **Match PO & Check Approval** — The invoice is matched against its purchase order in
   the ERP: the PO must exist, the vendor must be active, and the invoice total must be
   within the PO's open amount (2% tolerance). Approval is required when the invoice does
   **not** match its PO, or when the total exceeds 10,000 USD.
4. **Build Approval Package** — For invoices that require approval, the evidence an
   approver needs (GL account, cost center, named approver, payment terms, vendor risk,
   goods-receipt reference, a summary of the invoice lines) is gathered into a structured
   approval package with a recommendation. Packages with missing evidence are flagged for
   AP review instead of being sent to the approver.
5. **Review & Approve** — An accounts-payable reviewer reads the package and the
   recommendation and either approves or rejects the invoice. A rejected invoice ends the
   process; the rejection reason is recorded.
6. **Post to ERP & Pay** — Every approved invoice, and every matched invoice that never
   needed approval, is posted in the ERP / AP portal and submitted for payment. Posting
   closes the invoice.

## Decision points

- Valid? → no: **Rejected** (structurally incomplete invoice).
- Approval needed? → no: **Auto-approved** — the invoice skips steps 4 and 5 and goes
  straight to posting.
- Approved? → no: **Rejected** (reviewer decision).

## Actors

- **Vendor** — sends the invoice.
- **Accounts Payable (AP) reviewer** — reviews approval packages, approves or rejects.
- **Approver** — the budget owner named on the package (the AP reviewer acts on their behalf in this lab).
- **ERP** — system of record for purchase orders and payments.

## Business rules

- PO matched = PO exists **and** vendor active **and** invoice total within the PO open amount (2% tolerance).
- Approval required = **not** PO matched **or** invoice total > 10,000 USD.
- Structurally valid = PO number **and** total amount present.
- Ready to post = PO matched **and** not already posted **and** (no approval needed **or** approved).

## Data captured on the invoice record

Vendor Name, Vendor Tax ID, Invoice Number, Invoice Date, PO Number, Total Amount, Currency,
Due Date, Processed Timestamp; PO Matched, Approval Needed, Posted To ERP; approval inputs
(GL Account, Cost Center, Approver, Payment Terms, Vendor Risk Score, Receipt Reference,
Invoice Line Summary); approval outputs (evidence state, missing fields, recommendation,
approval package, agent timestamp, lifecycle state); reviewer decision (reviewed by, reviewed at).

## Security and privacy constraints

Vendor tax IDs, bank details, and invoice amounts are confidential business data. They may be
stored on the invoice record and shown to authorised AP users, but must not be written to logs,
chat transcripts, or documentation.
