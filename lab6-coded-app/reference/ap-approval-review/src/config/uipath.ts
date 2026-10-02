/**
 * App configuration that is NOT part of the OAuth/SDK config.
 *
 * OAuth (clientId, scope, orgName, tenantName, baseUrl, redirectUri) lives in
 * `uipath.json` at the project root and is injected as <meta name="uipath:*">
 * tags by the @uipath/coded-apps-dev Vite plugin (dev) or the platform (prod).
 * Nothing here is a secret.
 */

/**
 * FACILITATOR / PARTICIPANT: replace with the Id of the tenant-scoped
 * `AP_Invoice_<user_name>` entity on customersuccessamer / Training.
 *
 *   uip df entities list --output json
 *
 * and copy the `id` (a GUID) of the row whose `name` is AP_Invoice_<user_name>.
 * The app refuses to start the worklist while this is still the placeholder.
 */
const INVOICE_ENTITY_ID = 'REPLACE_WITH_AP_INVOICE_ENTITY_ID';

export const UIPATH_CONFIG = {
  invoiceEntityId: INVOICE_ENTITY_ID,
  /**
   * AP_Invoice_<user_name> is tenant-scoped, so NO folder key is passed to any
   * Data Fabric call. Keep this empty; `--folder-key` is only used by
   * `uip codedapp deploy`. (Passing the deployment folder here is the classic
   * "not found only when a folder is supplied" mistake from the lab.)
   */
  invoiceFolderKey: '' as string,
  /**
   * Rows per table page. Deliberately small: the seeded AP_Invoice_<user_name> entity holds
   * about eleven records, so 5 per page gives three pages and lets the pager be exercised.
   * Raise it (the skill suggests 25–50) once the entity holds real volumes.
   */
  pageSize: 5,
  /** Rows per SDK request while following the cursor. */
  fetchPageSize: 100,
  /** Safety cap on cursor pages (100 rows each) so a runaway entity cannot hang the UI. */
  maxFetchPages: 50,
} as const;

const GUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True once the placeholder has been replaced with a real entity GUID. */
export function isEntityIdConfigured(): boolean {
  return GUID_RE.test(UIPATH_CONFIG.invoiceEntityId);
}

/** Folder-scope options spread into every Entities call (empty for tenant-scoped entities). */
export const folderScope = UIPATH_CONFIG.invoiceFolderKey
  ? { folderKey: UIPATH_CONFIG.invoiceFolderKey }
  : {};
