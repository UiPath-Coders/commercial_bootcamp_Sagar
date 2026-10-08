/**
 * App configuration that is NOT part of the OAuth/SDK config.
 * OAuth (clientId, scope, orgName, tenantName, baseUrl, redirectUri) lives in
 * uipath.json and is injected as <meta name="uipath:*"> tags. Nothing here is a secret.
 */
export const APP_CONFIG = {
  /**
   * Tenant-scoped Data Fabric entity, addressed by name (getByName,
   * getRecordsByName, getRecordByName, updateRecord({ name }, ...)).
   * No folder key is ever passed: tenant entities return "not found" with one.
   */
  invoiceEntityName: 'AP_Invoice_Sagar',
  /** Rows per table page. The seeded entity holds about eleven records, so 5 gives three pages. */
  pageSize: 5,
  /** Rows per SDK request while following the cursor. */
  fetchPageSize: 100,
  /** Safety cap on cursor pages so a runaway entity cannot hang the UI. */
  maxFetchPages: 50,
  orgName: 'customersuccessamer',
  tenantName: 'Training',
} as const;
