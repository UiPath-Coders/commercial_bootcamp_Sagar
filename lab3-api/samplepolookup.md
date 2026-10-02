# Sample PO-Lookup Request

The `POMatch_<user_name>` Python Coded Function calls the mock ERP purchase-order service.
The included mock ERP runs at `http://localhost:8080` by default. Replace `<erp_api_url>` with that value for
local work, or with a facilitator-hosted HTTPS base only for a cloud-robot run.

## Health check

```
GET <erp_api_url>/health
```

Expected response:

```json
{ "ok": true, "service": "erp-po-api" }
```

## PO lookup

```
POST <erp_api_url>/api/po-lookup
Content-Type: application/json

{
  "vendorName": "Vertex Analytics Corp.",
  "poNumber": "PO-2026-0405",
  "invoiceTotal": 22700.00,
  "currency": "USD"
}
```

Expected response:

```json
{
  "po": {
    "found": true,
    "vendorActive": true,
    "openAmount": 22700.00,
    "currency": "USD"
  }
}
```

An unknown PO returns `"found": false` with `openAmount` `0`.

## How `po_lookup` uses the response

- `po_matched` is `true` only when `po.found` is `true`, `po.vendorActive` is `true`, and
  `invoiceTotal` is within 2% of `po.openAmount`.
- `approval_required` is `true` when `po_matched` is `false` **or** `invoiceTotal` is greater
  than `10000`.
- For the sample above: `po_matched = true`, `approval_required = true` (over the threshold).
- Any unsuccessful or malformed response, or a response without a `po` object, must populate
  `error_type` and `error_message` instead of guessing.

## Mapping to the invoice record

`process_invoice_queue` fills the request from the `AP_Invoice_<user_name>` record referenced by
each queue transaction: `VendorName → vendorName`, `PONumber → poNumber`, `TotalAmount → invoiceTotal`,
`Currency → currency`, and writes `po_matched → POMatched`, `approval_required → ApprovalNeeded`.
