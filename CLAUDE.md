# Commercial Bootcamp: rules for Claude Code

## How this repo is used
- This is the golden repo `UiPath-Coders/commercial_bootcamp_lab_assets`. Each participant has a private copy
  `UiPath-Coders/commercial_bootcamp_<user_name>` (plain copy, no shared git history, no upstream remote).
- Sessions open on the plain folder `commercial-bootcamp/`, which holds `commercial_bootcamp_lab_assets/` and
  `commercial_bootcamp_<user_name>/`. A copy of this file sits at the `commercial-bootcamp/` root.
- Build only inside `commercial_bootcamp_<user_name>/<lab folder>`. Never edit `commercial_bootcamp_lab_assets/`.
- `<lab>/reference/` holds working answers. Copy their shapes; never their `_Reference` names or keys.
- Synthetic data, USD only. Never commit or save VendorTaxId values, signed URLs, tokens, or colleagues' emails,
  and never print them, with one exception: the Lab 1 prediction review shows predicted Vendor Tax IDs so the user
  can confirm them. Later tables show VendorTaxId as match/miss only.

## Tenant [TENANT-SPECIFIC: customersuccessamer / Training on https://staging.uipath.com]
- If `uip login status` shows another tenant, run `uip login tenant set Training`.
- On a 401, run `uip login refresh --login-validity 60` once. If it still fails, ask the user to run `uip login`.
- Participant folder path is always `Agentic Bootcamp/APAutomation_<user_name>`. Use the full path for
  `--folder-path`, for SDK `folder_path`, and for queue calls. The bare name returns
  `400 Folder does not exist or the user does not have access`.
- Data Fabric entities are tenant-scoped. Never pass a folder key to `uip df`. Read only `AP_Invoice_<user_name>`;
  the other `AP_Invoice_*` entities belong to other participants.
- [TENANT-SPECIFIC] Machine "Default Serverless" key `49d9ff03-a061-4c5c-88f0-613455cedbaf` and robot
  "Agentic Labs Robot" are assigned on the parent `Agentic Bootcamp` and inherited by every sub-folder.
  - Check with `uip or folders runtimes <folder-key>` (expect Serverless Total 1; Connected/Available 0 is normal)
    and `uip or users list-in-folder --folder-key <key> --include-inherited`.
  - `uip or machines list --folder-key` shows direct assignments only. An empty list is normal.
  - Never create a machine, machine template, robot account, or role.
- Start every job like this:
  `uip or jobs start <process-key> --folder-key <key> --runtime-type Serverless --machine-keys <default-serverless-key> --input-arguments '<json>' --wait-for-completion`.
  Never force the Unattended runtime type.

## uip CLI traps (uip 1.200.1)
- `--output-filter` needs an explicit `--limit`. It applies to the `Data` contents: write `[?x]`, not `Data[?x]`.
- `uip or folders list --name` requires `--all`. Prefer `uip or folders list --limit 200` and match client-side.
- `queues get`, `jobs get`, `jobs logs` and `processes get` take the key only. They reject `--folder-key`.
- Publish a package: pack, then `uip or packages upload <nupkg>` WITHOUT `--folder-key` (with it: "Error resolving
  package feed"), then `uip or processes create --name <n> --package-key <id> --package-version <v> --folder-key <key>`.
- Pin package versions on install. Unpinned installs fail with "No versions found":
  `UiPath.DataService.Activities` 25.9.10, `UiPath.UIAutomation.Activities` 26.10.3. One package per install call
  (see RPA projects).
- `uip df` re-cases acronyms (`PoNumber`, `PoMatched`, `GlAccount`) and omits null fields. `PostedToERP` stays
  as is. The Python and TypeScript SDKs return schema names. Read case-insensitively, write schema names, and
  treat a missing PostedToERP as false.
- Never run `uip or jobs get` on Lab 3 jobs where the user can see the output. It prints EnvironmentVariables,
  which hold the signed ERP URL. Use `uip or jobs list --all-fields`. Never paste job environment variables.
- Read records with `uip df records query` and `selectedFields` that exclude VendorTaxId and ApprovalPackageJson
  whenever the output is shown or saved. Show TotalAmount only when the prompt asks for it, and never save amounts
  in the repo.
- `uip or processes get` shows `EntryPointPath ""` and `Arguments null` even when the binding is correct. Get
  schemas with `uip or packages entry-points <package>:<version>`.

## Solutions (`uip solution`)
- `deploy run` ALWAYS creates a new child folder named by `--folder-name` under `--parent-folder-path`/`-key`.
  - It cannot target an existing folder.
  - It cannot install under a Solution-type folder: 400 / errorCode 4023.
  - On a name collision it renames the folder (`X 1`).
- uip 1.200.1 has no `deploy upgrade`. A new version needs a new deployment name (e.g. `<name>_v101`), which
  appears as a sibling folder. Tell the user the old deployment stays until the facilitator uninstalls it.
  Never uninstall on your own.
- If `deploy run` returns `HTTP 500 Execution Timeout`, rerun the identical command once.
- Keep `.uipx` manifests in git. Ignore only build zips.
- Setup smoke test [TENANT-SPECIFIC]: deploy `NA_HelloWorld_<user_name>` as a new folder under
  `Shared/BootCampSmoke` (Standard folder). `Shared/BootCampTest` is a Solution folder; never target it.
- `uip rpa run` needs `--file-path Main.xaml`.
- `deploy status` takes the PipelineDeploymentId from `deploy run` output, not the name.

## Git
- Commit only the current lab folder (`git add <lab folder>`), on branch `main`. Show `git status` first.
- Before every commit, confirm nothing staged is `.env`, `.uipath/`, `*audit-export*`, `userProfile/`, `deploy-config*.json`,
  a nupkg, or a file containing an access_token value (a JWT, `access_token=ey…`, or a signed URL). Code, tests
  and docs that only name access_token are fine: POMatch main.py, mock-erp/create-access-token.mjs, SDDs that
  describe the rule.
- If `git config user.email` is empty, ask the user for it. Do not commit under a hostname identity.

## RPA projects (Labs 2 and 4)
- VB is case-insensitive. Never name a variable like an argument; validate/build won't catch it, only a null
  output at runtime shows it. Lab 2: `processedCount` shadows `ProcessedCount`. Lab 4: Main's outputs are
  un-prefixed (Posted, PostingId, RecordId, ErrorMessage, WasAlreadyPosted); never declare `posted`,
  `postingId`, `recordId`, `errorMessage` in Main; prefix locals (`portalPostingId`).
- Analyzer warnings that contract arguments don't match `^in_`/`^out_` are expected. Keep the contract names.
- Install one package per call: `uip rpa packages install --packages 'id=<id>,version=<v>'`. Several ids in one
  call fail with "too many arguments".
- If `uip rpa validate` reports "Helm did not become ready within 60s", retry once. Do not kill Helm.
- If `uip rpa data-fabric-entities install --add AP_Invoice_<user_name>` says "not found in the connected Data
  Fabric tenant", the local Studio is signed in to another tenant.
  - Copy `lab2-rpa/reference/Invoice_Intake_RPA_Reference/.entities/EntitiesStore.json` (Lab 4: copy your Lab 2
    store). Replace the entity id, every field id by field name, the SystemUser entity id and its Name field id
    with `uip df entities get <id>` values. Keep the SQL type names (NVARCHAR, BIT, DATETIMEOFFSET,
    UNIQUEIDENTIFIER) in `Fields[].SqlType` and in the embedded `EntitiesJson` string.
  - Set the store's top-level `Namespace` to the project name, the same value as `project.json`
    `entitiesStores[].namespace`. A stale Namespace fails with "Cannot create unknown type"; restarting Helm is
    not the fix.
  - Register it in `project.json` `entitiesStores` and tell the user.

## Lab 1: IXP
- There is no retrain command. Confirming labels triggers retraining (about 20-35 s); wait until the model
  version goes up.
- If `labellings get-predictions` shows documents without predictions, wait a minute and read again before
  reviewing.
- Total Amount may already be correct on all five. Report that rather than inventing a defect. Still harden the
  instruction when asked.
- No command runs a specific version on local files. `labellings get-predictions` returns the latest model;
  after publishing, latest = live.
- Dates come back as `YYYY-MM-DDT00:00:00Z`. Compare them as dates. Total Amount (Number) is a bare decimal.
- `reference/expected-extractions.json`: records are under `invoices[]` → `expected`; `lab1_ixp_documents` only
  lists filenames.

## Lab 2: RPA intake + extraction agent
- The uipath-agents skill has no IXP tool recipe. Copy
  `lab2-rpa/reference/Invoice_Extraction_Agent_Reference/**/resources/VendorInvoiceIXP/resource.json`, set
  `projectName` = display title `Vendor Invoice <user_name>` and `versionTag` = `live`, and keep `guardrail.policies []`.
- Deploy the agent as a solution with `--parent-folder-key <APAutomation key>`. It lands in
  `Agentic Bootcamp/APAutomation_<user_name>/Invoice_Extraction_Agent_<user_name>`.
- Run Job must set FolderPath `Agentic Bootcamp/APAutomation_<user_name>/Invoice_Extraction_Agent_<user_name>`
  (the reference passes it as `in_AgentFolderPath`).
- Set `InvoiceLifecycleState = "EXTRACTED"` on create, as the reference does.

## Lab 3: Python Coded Function (POMatch_<user_name>)
- `mkdir POMatch_<user_name> && cd` into it, then `uip function new POMatch_<user_name> --language py`.
  Ignore its `uipath init` hints.
- There are no description/authors flags. Edit `pyproject.toml`. Never use `&` or `<` in description or authors:
  pack writes them unescaped into the .nuspec.
- Python SDK login is per folder. Run `uv run uipath auth --staging` inside the folder that has pyproject.toml;
  it writes `./.env` and `./.uipath/.auth.json`. Make sure both are git-ignored.
- First thing in main.py: `logging.getLogger("httpx").setLevel(logging.WARNING)`. At INFO, httpx logs the full
  URL including access_token.
- `folder_path` default = `Agentic Bootcamp/APAutomation_<user_name>`.
- SDK `create_transaction_item` / `complete_transaction_item` return `response.json()`. An empty 200/204 raises
  JSONDecodeError although the call succeeded. Catch it, and never leave a transaction In Progress.
- Publish with `uip function pack`, then `uv run uipath publish --tenant`. Create one process per entry point:
  `uip or processes create --name POMatch_<user_name>_<ep> … --entry-point <ep> --folder-key <key>`.
- After `uip function init` plus `uip or processes update-version`, every process is silently rebound to the
  first entry point.
  - Re-bind each with `uip or processes update <key> --entry-point <ep>`.
  - Verify with a job or `uip or packages entry-points`.
  - `update-version --package-version` takes one key per call.
- Pass the signed ERP URL per job: `--environment-variables "ERP_PO_LOOKUP_URL=<url>"`.
  - Also set it as a process env var on `_process_invoice` and `_process_invoice_queue`
    (`uip or processes update <key> --environment-variables "…"`). Maestro cannot pass job env vars.
  - Never print the token.
- Function input keys are snake_case (`record_id`). get_invoice_status returns booleans: unset ApprovalNeeded →
  true, unset PostedToERP → false.
- Most reference tests are reference-internal. Run only `test_rules.py`, `test_po_lookup_live.py` and
  `test_po_lookup_errors.py` against participant code (`lab3-api/reference/README.md` lists what they import). Use `POLookupInput` and the match_reason codes MATCHED,
  PO_NOT_FOUND, VENDOR_INACTIVE, OUTSIDE_TOLERANCE.
- `uip function run <ep> --input '<json>'` and `uv run uipath run <ep> '<json>'` both work locally.
- Check the signed URL by decoding only the token's `exp`; never print `apiUrl` or the URL itself.
- `uipath` CLI commands load `./.env`; a bare `uv run python -c` does not (BaseUrlMissingError). Use `uipath run` /
  `uip function run` or `load_dotenv()`.
- `uip or processes get` does not show environment variables. Prove a process env var with a job started without
  `--environment-variables`.

## Lab 4: PostToERP_<user_name> (browser UI automation on serverless)
- Discover every target with the uipath-rpa skill's live UI exploration against the HOSTED portal (the Portal
  URL on the bootcamp page, signed in as ap_user / passwod) in Chrome. Keeping the Object Repository it builds is
  fine. The participant grants screen-recording or accessibility permission if asked. `uip rpa debug start`
  cannot reach Data Service locally; done means the serverless job against the hosted portal.
- If browser capture reports "Cannot communicate with the browser / UiPath extension", do NOT capture Chrome as a
  desktop application: that yields macOS accessibility selectors (`<ax role='AX…'>`, window titles with the
  Chrome profile name) that build fine and never run on the serverless robot. Fall back to the element ids in
  `mock-erp/README.md` as `<webctrl id='…' tag='…' />` under `<html app='chrome.exe' title='Globex AP Portal*' />`
  and say so. Pre-build check: `grep -c "role='AX" PostInvoiceInPortal.xaml` prints 0.
- Never explore or test against a localhost portal in this project. A captured Object Repository screen stores
  the URL it was recorded on, and the serverless robot then opens that URL instead of `PortalUrl` (proven
  2026-10-02: the same package fails with `Url="http://localhost:8080/portal/"` in `.objects/` and passes with
  the hosted URL there; nothing else changed). Before building, `grep -rl localhost` on the project (excluding
  `.local`) must be empty, `.objects/` included; replace any hit with the hosted URL.
- Portability (targets captured in the participant's Chrome must work on the serverless robot):
  - element selectors on stable `id` (+ tag) only; no idx, positions, visible text, css-selector or aaname chains;
  - window selector `<html app='chrome.exe' title='Globex AP Portal*' />`, no `url`, no host; the Use Browser
    URL comes from `PortalUrl`;
  - Use Browser card: InteractionMode Simulate; URL bound to `PortalUrl`.
  - Cloud symptom "nothing found, not even BODY, for ~120 s" = the robot opened the wrong page: a localhost URL in
    `.objects/`; never the element ids.
- The reference `lab4-rpa/reference/PostToERP_Reference/PostInvoiceInPortal.xaml` is for comparison, not copying.
- First portal step: an optional sign-in in Try/Catch with a short timeout (`#input-portal-username`,
  `#input-portal-password`, `#btn-sign-in`, ap_user / passwod). The local portal has no form.
- `RecordId` is one InOut String argument.
- Query with a sort only and filter in VB LINQ. Use `Guid.Parse` in an Assign.
- Set `.Id` on the entity object passed to Update Entity Record.
- After a confirmed posting, set `PostedToERP = True` AND `InvoiceLifecycleState = "POSTED"`, as the reference
  `MarkInvoicePosted.xaml` does.
- Gate on `uip rpa build`. Per-file validate may false-fail on UIA types.
- Cloud runs pass `PortalUrl = https://commercial-bootcamp-mock-erp.onrender.com/portal/` [TENANT-SPECIFIC host].
  The first request may take 30-60 s (Render cold start).

## Lab 5: coded LangGraph agent
- Extend the entity once: `uip df entities update <id> --file addfields.json` with `{"addFields":[…]}`.
  - Use type `MULTILINE_TEXT` for ApprovalPackageJson (never MULTILINE_MAX).
  - Use `DATETIME_WITH_TZ` for AgentProcessedAt and ReviewedAt.
  - The total is 27 user fields.
- `uip codedagent run` / `eval` reuse the uip session. No `.env` is needed.
- Never keep VendorTaxId in graph state. `uip codedagent run` prints the full state after every node.
- Retry guard: also never downgrade APPROVED, REJECTED or POSTED, even without an ApprovalPackageJson.
- Eval CSV: `InvoiceReference` has no schema field. Map new ids by InvoiceNumber (TRAIN-*-100N). Rename the
  template's snake_case expected keys to the camelCase contract.
- The live eval writes to the six records. AP-TRAIN-1003 is then already prepared. Before the deploy test, clear
  its six agent fields (after the user confirms) or use an untouched record. Prove "no second LLM call" on a
  gate-4 record (AP-TRAIN-1006), not 1003.
- Deploy:
  - `uip codedagent deploy --tenant`, then
    `uip or processes create --name Invoice_Approval_Agent_<user_name> --package-key Invoice_Approval_Agent_<user_name> --package-version <v> --folder-key <key>`.
  - Run with `uip or jobs start <key> --folder-key <key> --input-arguments '{"recordId":"<id>"}' --wait-for-completion`.
  - `deploy --folder` fails (it means a folder feed). `codedagent invoke` reaches My Workspace only.
- `Governance policy fetch failed … 403 policy_service_forbidden` in job logs is expected. Ignore it.
- The handoff card lives at `lab5-coded-agent/canonical-handoff.md`.
- `uip df records update` echoes the whole record, including VendorTaxId. Do not print its response; show `Id` only.
- Prove "no LLM call" with `uip traces spans get <job TraceId>`. `uip or jobs traces` returns 404 for coded agents
  created with `processes create`.

## Lab 6: coded app (ap-approval-review-<user_name>)
- `uipath.json` baseUrl = `https://staging.uipath.com` (the plain host). This overrides the skill's api-subdomain
  rule; the deployed app gets the api host injected.
- Use bare Tailwind styling. Do not stop to ask the scaffold questions; the prompt answers them.
- Add `.uipath/` to the app's `.gitignore`.
- Address entities by name: `getByName`, `getRecordsByName`, `getRecordByName`, `updateRecord({ name }, id, patch)`.
  No entity-id placeholder (the reference still has one and uses the deprecated `updateRecordById`; don't copy that).
- Approve and Reject are both enabled when InvoiceLifecycleState is READY_FOR_APPROVAL or NEEDS_AP_REVIEW and
  ApprovalNeeded is true. On NEEDS_AP_REVIEW show a one-line note that approval evidence is incomplete
  (MissingApprovalFields).
- When the user must approve something, always state the InvoiceNumber and VendorName of the exact row. The table
  has no Record ID column. Afterwards check that no other record changed to APPROVED/REJECTED.
- Deploy: `npm run build`, then `uip codedapp pack dist -n <name> --version <v> [--author "<name>"]` (`--author`,
  never `-a`; the skill table is wrong; no `--reuse-client`, it doesn't exist), then `uip codedapp publish -n <name> --version <v> -t Web`, then
  `uip codedapp deploy -n <name> --folder-key <key> < /dev/null`.
  - `pack --dry-run` says "Package created successfully" but writes nothing.
  - The URL is `https://customersuccessamer.staging.uipath.host/<slug>` [TENANT-SPECIFIC].
- After any change following a deploy, bump the version and pack/publish/deploy again.

## Lab 7: Planner
- The PDD is plain writing. The planner has no PDD path; do not start SDD Phase D during the PDD step.
- Write SDDs only for RPA, agents, the coded app and BPMN. Functions and the IXP model go inside their host SDDs.
- Tasks file name: `implementation-tasks.md`. Put it in every Planner Handoff header.
- pandoc is not installed. Build the .docx with the docx skill; if `require('docx')` fails, `npm install docx` in a
  temp folder outside the repo.
- Inspect with read-only commands only.
- There is no `uip codedapp list`. Verify the coded app with `uip or packages list` (package
  ap-approval-review-<user_name>) and an HTTP check of its URL.
- Before the .docx and before committing, scan the documents for invoice amounts and tax IDs; use format
  descriptions, never sample values.

## Lab 8: Platform inspection
- Show inherited users by role and count only. Never save colleagues' emails to the repo.
- Check machines on both the folder and `Agentic Bootcamp`.
- Check jobs in the solution sub-folders separately. `jobs list --folder-key <parent>` excludes them.
- `uip or jobs logs --level Warning` returns HTTP 400 (log entries say `Warn`). List without `--level` and count
  levels client-side.
- The parent also holds a second machine template, Agentic Labs Unattended Robot. It is expected; do not report it.
- `--output-filter` needs `--limit` on `uip df records query` too. `bucket-files list` and `df records query` return
  `Data.Items`.
- "Resource overwrites read from …uipath.json (0 entries)" and the Lab 5 governance 403 log at Error level on
  Successful jobs. They are noise; report them as such.

## Lab 9: Governance (tool-use draft, access review, tenant inventory, my-ip, commit)
- Never create or deploy AOps policies, access policies, compliance packs, IP ranges, invitations or memberships.
- ToolUsePolicy has no Function resource type. The POMatch functions cannot be governed.
  - Selectors take process Key UUIDs. Keep the caller as `BIND_AFTER_LAB10:InvoiceApprovalProcess_<user_name>`.
  - `access-policy evaluate` needs `--actor-process-type` and `--actor-process-id`.
- `check-access` returns at most 10 results. Query per `--service`: documentunderstanding, dataservice, reinfer,
  orchestrator, processmining, testmanager, centralizedaccess (not du or identity); the totals must add up to the
  unfiltered TotalCount. Response keys are PascalCase.
- `--folder-id` takes the folder KEY GUID, not the numeric Id.
- If an audit export runs at all, write it to `lab9-governance/audit-export/` (git-ignored) or outside the repo.
- Save the draft as `lab9-governance/access-policy-<slug>.json` + `.spec.md`, not /tmp. The `BIND_AFTER_LAB10:`
  caller deliberately overrides the skill's no-placeholder rule; no Spec-approval gate, because nothing is created.
- `tenants services list` has no status: use `uip admin tenants get <id>` → `TenantServiceInstances[].Status`.
  `list-available --region` is not region-filtered; filter on SupportedRegions.
- The participant group holds Folder Administrator on Agentic Bootcamp on purpose (Lab 2 creates the sub-folder).
  Report it as a known, accepted grant.

## Lab 10: Maestro BPMN (these runtime rules beat registry templates; all of them pass validate)
- Reference: `lab10-maestro-bpmn/reference/InvoiceApprovalSolution_Reference/InvoiceApprovalProcess_Reference/InvoiceApprovalProcess_Reference.bpmn`.
  Its release keys and folder id are `REPLACE_WITH_…` placeholders; use the keys from the Step 1 readiness table.
- `Orchestrator.StartJob`: every context input carries `type="string"`. `releaseKey` is a literal process Key
  (not `=bindings.…`). Otherwise the instance fails with `170005 … Required field 'releaseKey' missing`.
- Call agents with `Orchestrator.StartJob` and the agent's release key. `Orchestrator.StartAgentJob` is
  unrunnable: the validator forbids releaseKey and the runtime requires it. Coded agents have processType Agent.
- Variable ids have no underscores (`VarRecordId`, never `Var_RecordId`). Underscores are stripped at runtime.
- Set variables with `<uipath:type value="BPMN.Variables">` plus a `custom="true"` output with `source="=js:…"`.
  `BPMN.ScriptTask` with `source="=result.response"` never sets the target variable.
- Add `<uipath:inputSchema type="jsonSchema">` per task. Map outputs per argument:
  `<uipath:output name="po_matched" source="=po_matched" …>`.
- Pack and refresh do not derive `entry-points.json` (FileName input) or `bindings_v2.json` (v2.2, name +
  folderPath per process). Write both by hand from the BPMN, then refresh.
- Timer loop: `PT2M` timer → `PollCount + 1` → get_invoice_status. Loop while NEEDS_AP_REVIEW/READY_FOR_APPROVAL and
  PollCount < 6 (about 13 minutes), then end Held. Never use PT30S: it starts a serverless job every ~40 s per waiting instance.
- Before debug and before pack: refresh, grep `resources/` for `access_token` / `environmentVariables` (refresh
  copies process env vars into resource files), clear them with
  `uip solution resources edit <key> --patch '{"environmentVariables":""}'`. Parse refresh/edit JSON with
  `2>/dev/null`; INFO lines on stderr break `json.load`.
- After pack: grep the zip (with nested nupkgs) for `access_token=`, not the bare word. Then publish.
- After publish (config get reads a published package): `uip solution deploy config get <package> -d <file>
  --package-version <v>`, then `uip solution deploy config link <file> <name> --name <name> --folder-path
  "Agentic Bootcamp/APAutomation_<user_name>"` for each of the 5 Lab processes. The default config installs copies.
- Run:
  `uip maestro bpmn process run "<ProcessKey>:<version>" <solution-folder-key> --release-key <key> --feed-id <feed> --inputs '{"FileName":"<file in InvoiceInbox_<user_name>>"}'`.
- `process run` returns a JobKey; it is also the instance id. Monitor with
  `uip maestro bpmn instance element-executions <id> --folder-key <solution-folder-key>`; live variables
  (PollCount) with `uip maestro bpmn instance variables <id> --folder-key <key>` → `Data.Globals`.
  `job traces` prints nothing and `instance global-variables` returns 404 while running. A failed instance's
  Maestro job can still show Successful.
- Debug with a file whose record is already POSTED; never with 007/009 (Steps 4-5 need them unused).
- Debug with `uip maestro bpmn debug` before packaging. Every debug run leaves a Studio Web solution; list the ids
  for cleanup.
- Reviewer path: tell the user to approve VA-INV-40592 (Vertex Analytics), not TRAIN-VA-1006 (a Lab 5 eval row
  from the same vendor).
- `.gitignore`: the root file already keeps `.uipx` manifests and ignores build zips (`**/*_out/`, versioned
  `*.zip`), `**/userProfile/`, `**/.uipath/` and `deploy-config*.json`. Do not add `*.uipx` back.

## Challenge (homework): Maestro Flow
- The participant builds this one alone. Guardrails only; do not volunteer a design, a node list or a prompt.
- Build only in `commercial_bootcamp_<user_name>/challenge-maestro-flow/`, as a new `.flow` project in its own
  solution. There is no reference solution for it; do not borrow from `lab10-maestro-bpmn/reference/`.
- Never modify the published Lab 2-6 projects, their releases, or the user's Lab 10 BPMN solution and folders.
- Invoice 011 (`challenge-maestro-flow/commercial-invoice-011-contoso-logistics.pdf`, CLL-2026-3418) is reserved
  for the reviewer-path run. Do not use it for debug or test runs. 006 and 010 end Held by design.
- Every wait for a human gives up after about 15 minutes and ends the instance in a clear state. No faster poll
  than the Lab 10 cadence.
- Never print, save or commit tokens or signed ERP URLs. `challenge-maestro-flow/*/resources/` is gitignored for
  the same reason as Lab 10; still grep resources and packs for `access_token=` before publishing.
- Each solution deploy creates a new child folder under `APAutomation_<user_name>`. Tell the user its name and
  list leftover folders for cleanup.
