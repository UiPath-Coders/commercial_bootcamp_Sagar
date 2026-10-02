# Lab 4 reference implementation

`PostToERP_Reference` is a complete, compiling cross-platform XAML answer for the Day 1 Lab 4 prompt.

## Workflow map

| File | Responsibility |
|---|---|
| `Main.xaml` | orchestrate one posting, handle “nothing ready,” and keep failed records unposted |
| `GetNextReadyInvoice.xaml` | read records oldest-first, pick the first one that is ready to post, and return the four portal values |
| `PostInvoiceInPortal.xaml` | sign in if the portal asks, drive all eight browser steps using stable IDs, and verify confirmation |
| `MarkInvoicePosted.xaml` | set `PostedToERP = true` and `InvoiceLifecycleState = POSTED` on the selected record after confirmation |
| `.entities/EntitiesStore.json` | offline entity metadata that lets the project compile from a clone |

`Main.xaml` defaults to `http://localhost:8080/portal/`, so local portal development works without editing
the project input.

## Run the included portal

```bash
cd ../../../mock-erp
node smoke.mjs
node server.mjs
```

Walk the same screens manually on the hosted portal (Portal URL on the bootcamp page, ap_user / passwod). Participants explore and test only the hosted portal; see `../README.md`, "Portable selectors".

## Validate the project

In another terminal:

```bash
cd lab4-rpa/reference/PostToERP_Reference
uip rpa validate --min-severity warning
uip rpa build
```

The expected result is build `true`. The only possible analyzer warning is the tenant's Automation Hub
URL policy. See Runtime notes below about per-file validation.

## Before a live Data Fabric run

The checked-in entity store is an offline reference definition, not a claim that a public repository owns a
tenant entity. Bind `AP_Invoice_Reference` to the participant's tenant-scoped
`AP_Invoice_<user_name>` entity and confirm the live field IDs. Use the local portal URL for local Robot
execution, or pass the facilitator's reachable HTTPS `/portal/` URL when running on Automation Cloud.

## How the reference picks and updates a record

- **Selecting the invoice.** The Data Fabric query has no designer filter. It asks only for records sorted by
  `ProcessedTimestamp` (oldest first, up to 100). The workflow then picks the first record where
  `POMatched` is true, `ApprovalNeeded` is false, and `PostedToERP` is not true, using one LINQ expression.
  The designer's "Equals true", "Equals false" and "is null" filter operators looked fine at build time but
  failed at run time, so the rule lives in the workflow where anyone can read it. Empty yes/no fields are
  handled safely: an empty `PostedToERP` counts as "not posted yet", an empty `ApprovalNeeded` counts as
  "still needs approval". The log shows how many records were ready.
- **Retrying the query.** The query sits in a Retry Scope (3 retries, 5 seconds apart). Reading is harmless
  to repeat, so one short Data Fabric hiccup no longer fails the whole job.
- **Updating the right record.** The update puts the record Id on the entity object itself
  (`New AP_Invoice_Reference() With {.Id = in_RecordId, .PostedToERP = True, .InvoiceLifecycleState = "POSTED"}`)
  as well as in the activity's Record Id box, so the update always lands on the invoice that was just posted.
  The entity store includes `InvoiceLifecycleState` (text) for this write.
- **Signing in to the portal.** The hosted portal
  (`https://commercial-bootcamp-mock-erp.onrender.com/portal/`) shows a sign-in page, and without a
  session its searches come back empty. The first portal step therefore tries to sign in with the shared
  training account printed on that page (`ap_user` / `passwod`), inside a Try Catch that waits only
  about 5 seconds. On the local portal (`http://localhost:8080/portal/`) there is no sign-in page, the
  lookup times out, and the robot simply carries on. These are synthetic training credentials; in any real
  automation, keep credentials in an Orchestrator Credential asset and read them with Get Credential
  instead of typing them into the workflow.

## Safety behavior worth comparing

- Oldest-first sorting plus "first ready record" makes the selection deterministic.
- Empty portal fields fail before browser automation.
- Browser or Data Fabric errors are logged and rethrown.
- `PostedToERP` and `InvoiceLifecycleState = POSTED` are written only after the portal returns both a posting ID
  and the expected status.
- The write is idempotent and retried; the portal submission itself is not blindly retried.
- The query reads at most 100 records per run. That is plenty for a lab entity; a production process would
  page through results or filter on the server.

## Runtime notes

- **Run it on the serverless cloud robot.** Publish and start the process in Orchestrator. A local
  `uip rpa debug start` on a headless machine has no Data Service connection and stops with
  `EntityServiceException`; that is expected and says nothing about the workflow.
- **Trust `uip rpa build`.** Build is the real check. Validating the portal workflow file on its own can
  fail on a headless Mac with `Cannot create unknown type uix:NApplicationCard` even when the project builds
  cleanly.
- **Selectors are id-based and portable.** Every selector in `PostInvoiceInPortal.xaml` targets a documented id
  from `../../mock-erp/README.md`, and the Use Browser card follows the portable selector rules in
  `../README.md`. Participants find their own selectors by exploring the local portal; use this file to
  compare, not to copy.
