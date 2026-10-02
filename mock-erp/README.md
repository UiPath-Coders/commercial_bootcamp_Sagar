# Mock ERP — Globex Manufacturing (PO-lookup API + AP portal)

Part of `UiPath-Coders/commercial_bootcamp_lab_assets` (Office of the CFO · Invoice-to-Pay Approval).
One small Node server, **zero dependencies**, that plays the ERP the process talks to:

| Face | Used by | What it does |
|---|---|---|
| **PO-lookup API** | Lab 3 · `POMatch_<user_name>` (Python function) | `GET /health`, `POST /api/po-lookup` with the exact contract in `lab3-api/samplepolookup.md` |
| **AP portal** | Lab 4 · `PostToERP_<user_name>` (unattended browser UI automation) | `/portal/` — a finance-oriented AP workbench with realistic synthetic data and the same stable eight-step invoice-posting path |

Both read the same fixtures the rest of the bootcamp uses: `data/purchase-orders.json` (identical to
`lab5-coded-agent/lab-assets/vendor-invoice/api/po-lookup-responses.json`) and `data/vendors.json`
(the ten vendors of the invoice packets). All data is synthetic.

## Run it

```bash
cd mock-erp
node server.mjs            # http://localhost:8080  (PORT env var to change)
node smoke.mjs             # exercises every endpoint and exits 0
```

Or in Claude Code: *"Start the mock ERP in commercial_bootcamp_lab_assets/mock-erp with node server.mjs and
tell me the health-check result."*

Docker: `docker build -t bootcamp-mock-erp . && docker run -p 8080:8080 bootcamp-mock-erp`.

## Local first; the facilitator cloud service for cloud jobs

Nothing needs to be deployed to build and test the Lab 3 API against `http://localhost:8080` on a participant's
machine; local mode is open (no token) so that build loop stays frictionless. Lab 4 browser automation is the
exception: explore and test it against the hosted portal only, because UI capture stores the portal URL inside
the project and the cloud robot opens that URL (see `lab4-rpa/README.md`, "Portable selectors").

Only an Automation Cloud job creates a network boundary: its `localhost` is the cloud worker, not the
participant's laptop. For those runs the facilitator hosts this service once per bootcamp. The live service is:

| Placeholder in the labs | Value |
|---|---|
| `<erp_api_url>` | `https://commercial-bootcamp-mock-erp.onrender.com` — API base (`/health`, `/api/po-lookup`) |
| `<erp_portal_url>` | `https://commercial-bootcamp-mock-erp.onrender.com/portal/` — the AP portal |

Deploy repo: `UiPath-Coders/commercial-bootcamp-mock-erp` (a standalone copy with a `render.yaml`
Blueprint). Render auto-deploys on push to `main`.

### Hosted security (this service runs on the open internet)

Hosted mode is turned on with `BOOTCAMP_AUTH_MODE=required`. Machine-facing `/api` routes require a
**signed, expiring participant token** supplied in a generated API URL or a bearer header. The browser
portal deliberately uses the shared training login shown on its sign-in page (`ap_user` / `passwod`) because
all portal data is synthetic. Login/API rate limits, strict CORS, security headers, and request-size limits
protect the public service from casual abuse. `/health` stays public. Environment variables:

| Var | Purpose |
|---|---|
| `BOOTCAMP_AUTH_MODE` | `required` turns on hosted security (default `off` = open local mode) |
| `BOOTCAMP_SIGNING_SECRET` | ≥32-byte HMAC key that signs/verifies tokens (Render generates it) |
| `BOOTCAMP_COHORT_KEY` | optional extra cohort passphrase (tests); the static bootcamp key `cfo-invoice-2026-bb6579` (`STATIC_COHORT_KEY` in `server.mjs`, published on the tracker's lab pages) is always accepted |
| `BOOTCAMP_ALLOWED_ORIGINS` | comma-separated exact origins allowed to call `/api` from a browser |
| `BOOTCAMP_PORTAL_RATE_LIMIT_PER_MINUTE` | shared-login browser API limit per source IP (default 600) |

### Getting a participant API URL

Participants mint their own URL from the tracker's **"Generate my ERP API URL"** widget, which calls
`POST /auth/token` with the cohort key. The URL carries a short-lived signed token and can be pasted directly
into Claude Code. Bearer-token access remains supported for existing assets. A facilitator can also mint one directly:

```bash
BOOTCAMP_SIGNING_SECRET=... node create-access-token.mjs --participant <id> --hours 8 --base-url https://commercial-bootcamp-mock-erp.onrender.com
```

The server is stateless apart from the in-memory postings list; `DELETE /api/postings` resets a
participant's own list. On the free Render plan the service sleeps after ~15 min idle, so the first
request after a lull cold-starts (~30–60s), then it is fast.

## API

```
GET  /health                     → { "ok": true, "service": "erp-po-api" }              (public)
POST /auth/token                 → 200 { participantId, token, expiresAt, apiBaseUrl, apiUrl, portalUrl }
     body: { "cohortKey", "participantId", "hours" }   cohort-gated self-service mint (open CORS)
POST /api/po-lookup              → { "po": { "found", "vendorActive", "openAmount", "currency" } }
     body: { "vendorName", "poNumber", "invoiceTotal", "currency" }   (only poNumber is required)
GET  /api/po-lookup/:poNumber    → same shape (convenience)
GET  /api/vendors?q=<text>       → { "vendors": [ { vendorId, vendorName, taxId, status, openPurchaseOrders, … } ] }
GET  /api/postings               → { "postings": [ … ] }            what Lab 4 submitted (per participant)
POST /api/postings               → 201 { postingId, status: "SUBMITTED_FOR_PAYMENT", … }
DELETE /api/postings             → clears the caller's list
```

In hosted mode every `/api` route requires a generated `?access_token=<token>` URL,
`Authorization: Bearer <token>`, or the portal session cookie. The URL form is convenient for the workshop
but can appear in request logs, so tokens are short-lived and authorize synthetic data only. CORS is limited
to `BOOTCAMP_ALLOWED_ORIGINS`; in local mode the API is open. The `/auth/token` mint endpoint is deliberately
open to any browser origin because the cohort key is its gate.

## Portal login

The hosted AP portal uses one shared training account, printed directly on the sign-in page:

- Username: `ap_user`
- Password: `passwod`

Local mode still opens without a sign-in. Each hosted sign-in receives a separate expiring HttpOnly session,
so postings and API rate accounting do not collapse into one shared browser session.

Sign-in form element ids (hosted portal only; absent in local mode): `#input-portal-username`,
`#input-portal-password`, `#btn-sign-in`. A robot that must work against both portals signs in inside a
Try/Catch with a short timeout, so the missing form on the local portal is skipped. Without a session the
hosted `/api/*` routes return 401 and the vendor Search step returns no rows.

Both URLs at a glance: Lab 3 calls the **API** (`/api/po-lookup`, signed URL from the tracker widget); Lab 4
drives the **portal** (`/portal/`, shared login above). Pasting the portal URL into the Lab 3 function is the
most common mix-up.

## AP portal click path and element ids (Lab 4)

| # | Step in the lab | Element |
|---|---|---|
| 1 | Click **Enter vendor invoice** | `#btn-post-invoice` |
| 2 | Enter the **Vendor Name** | `#input-vendor-name` |
| 3 | Click **Search** | `#btn-search` → results in `#vendor-results` |
| 4 | Select the returned vendor row | `tr[data-vendor-id]` / radio `#vendor-row-<vendorId>` (a single match selects itself) |
| 5 | Click **Next** | `#btn-next-1` |
| 6 | Enter **Invoice Number**, **PO Number**, **Total Amount** | `#input-invoice-number`, `#input-po-number`, `#input-total-amount` |
| 7 | Click **Next** | `#btn-next-2` (review screen shows the PO check in `#review-po-status`) |
| 8 | Click **Post voucher & release for payment** | `#btn-submit-payment` → `#confirmation-id`, `#confirmation-status` = "Submitted for payment" |

Vendor ids are `V-1001` … `V-1010` in packet order (Northwind … Pacific Timber). Blue Harbor Catering is
`INACTIVE`; Pacific Timber has no open PO (`PO-2026-0489` returns `found: false`).

Lab 4 participants discover these targets by exploring the hosted portal with the uipath-rpa skill; the
selectors should end up id-based (`<webctrl id='…' tag='…' />`; vendor row
`<webctrl id='vendor-row-*' parentid='vendor-results-body' tag='INPUT' type='radio' />`) so they work on the
serverless robot. See `lab4-rpa/README.md` for the portable selector rules. The hosted posting counter restarts per session, so two runs can both return
`AP-2026-00001`.
