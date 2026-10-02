/**
 * AP_Invoice_<user_name> field system names, exactly as defined in
 * bootcamp-site/docs/commercial-process.md (PascalCase, no spaces).
 * Data Fabric record keys are case-sensitive; never re-case these.
 */
export const F = {
  // Data Fabric audit fields (row metadata, read-only)
  Id: 'Id',
  CreateTime: 'CreateTime',
  UpdateTime: 'UpdateTime',

  // Day 1 (Lab 2 / 3 / 4)
  ProcessedTimestamp: 'ProcessedTimestamp',
  VendorName: 'VendorName',
  VendorTaxId: 'VendorTaxId',
  InvoiceNumber: 'InvoiceNumber',
  InvoiceDate: 'InvoiceDate',
  PONumber: 'PONumber',
  TotalAmount: 'TotalAmount',
  Currency: 'Currency',
  DueDate: 'DueDate',
  POMatched: 'POMatched',
  ApprovalNeeded: 'ApprovalNeeded',
  PostedToERP: 'PostedToERP',

  // Day 2 approval inputs (Lab 5 seeds)
  GLAccount: 'GLAccount',
  CostCenter: 'CostCenter',
  Approver: 'Approver',
  PaymentTerms: 'PaymentTerms',
  VendorRiskScore: 'VendorRiskScore',
  ReceiptReference: 'ReceiptReference',
  InvoiceLineSummary: 'InvoiceLineSummary',

  // Lab 5 agent outputs
  ApprovalEvidenceState: 'ApprovalEvidenceState',
  MissingApprovalFields: 'MissingApprovalFields',
  AgentRecommendation: 'AgentRecommendation',
  ApprovalPackageJson: 'ApprovalPackageJson',
  AgentProcessedAt: 'AgentProcessedAt',
  InvoiceLifecycleState: 'InvoiceLifecycleState',

  // Lab 6 reviewer outputs (written by this app)
  ReviewedBy: 'ReviewedBy',
  ReviewedAt: 'ReviewedAt',
} as const;

export type FieldName = (typeof F)[keyof typeof F];

/** The seven approval inputs shown in the "Approval evidence" group. */
export const APPROVAL_INPUT_FIELDS: FieldName[] = [
  F.GLAccount,
  F.CostCenter,
  F.Approver,
  F.PaymentTerms,
  F.VendorRiskScore,
  F.ReceiptReference,
  F.InvoiceLineSummary,
];

/** Fields the UI depends on; if any is missing from the live schema the data-integrity banner shows. */
export const UI_DEPENDENT_FIELDS: FieldName[] = [F.InvoiceLifecycleState, F.AgentRecommendation, F.ReviewedBy];

/** Fields the approve / reject write touches; all must exist for a decision to be saved. */
export const DECISION_WRITE_FIELDS: FieldName[] = [F.InvoiceLifecycleState, F.ReviewedBy, F.ReviewedAt];

/** Columns rendered in the worklist table, in order, with the field each is backed by. */
export const TABLE_COLUMNS: { key: string; label: string; field: FieldName; sortable: boolean }[] = [
  { key: 'vendor', label: 'Vendor', field: F.VendorName, sortable: true },
  { key: 'po', label: 'PO Number', field: F.PONumber, sortable: false },
  { key: 'total', label: 'Total', field: F.TotalAmount, sortable: true },
  { key: 'approvalNeeded', label: 'Approval required', field: F.ApprovalNeeded, sortable: true },
  { key: 'lifecycle', label: 'Lifecycle State', field: F.InvoiceLifecycleState, sortable: true },
  { key: 'recommendation', label: 'Recommendation', field: F.AgentRecommendation, sortable: true },
  { key: 'updated', label: 'Updated', field: F.UpdateTime, sortable: true },
];

/** `InvoiceLifecycleState` values — one state machine, three writers (spec section). */
export const LIFECYCLE = {
  HOLD_PO_MISMATCH: 'HOLD_PO_MISMATCH',
  AUTO_APPROVED: 'AUTO_APPROVED',
  NEEDS_AP_REVIEW: 'NEEDS_AP_REVIEW',
  READY_FOR_APPROVAL: 'READY_FOR_APPROVAL',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  POSTED: 'POSTED',
} as const;

export type LifecycleState = (typeof LIFECYCLE)[keyof typeof LIFECYCLE];

/** KPI "Pending Review" counts these two states. */
export const PENDING_REVIEW_STATES: string[] = [LIFECYCLE.NEEDS_AP_REVIEW, LIFECYCLE.READY_FOR_APPROVAL];

/** KPI "Recommended for Approval" counts AgentRecommendation equal to this value. */
export const RECOMMENDED_FOR_APPROVAL = LIFECYCLE.READY_FOR_APPROVAL;
