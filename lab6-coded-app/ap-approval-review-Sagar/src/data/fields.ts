/**
 * AP_Invoice_Sagar field names exactly as discovered in the live schema
 * (uip df entities get). Data Fabric record keys are case-sensitive.
 */
export const F = {
  Id: 'Id',
  CreateTime: 'CreateTime',
  UpdateTime: 'UpdateTime',

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

  GLAccount: 'GLAccount',
  CostCenter: 'CostCenter',
  Approver: 'Approver',
  PaymentTerms: 'PaymentTerms',
  VendorRiskScore: 'VendorRiskScore',
  ReceiptReference: 'ReceiptReference',
  InvoiceLineSummary: 'InvoiceLineSummary',

  ApprovalEvidenceState: 'ApprovalEvidenceState',
  MissingApprovalFields: 'MissingApprovalFields',
  AgentRecommendation: 'AgentRecommendation',
  ApprovalPackageJson: 'ApprovalPackageJson',
  AgentProcessedAt: 'AgentProcessedAt',
  InvoiceLifecycleState: 'InvoiceLifecycleState',

  ReviewedBy: 'ReviewedBy',
  ReviewedAt: 'ReviewedAt',
} as const;

export type FieldName = (typeof F)[keyof typeof F];

/** The seven approval inputs ("Approval evidence" group and package checklist). */
export const APPROVAL_INPUT_FIELDS: FieldName[] = [
  F.GLAccount,
  F.CostCenter,
  F.Approver,
  F.PaymentTerms,
  F.VendorRiskScore,
  F.ReceiptReference,
  F.InvoiceLineSummary,
];

/** If any of these is missing from the live schema, the data-integrity banner shows. */
export const UI_DEPENDENT_FIELDS: FieldName[] = [F.InvoiceLifecycleState, F.AgentRecommendation, F.ReviewedBy];

/** Every field the approve / reject write touches. */
export const DECISION_WRITE_FIELDS: FieldName[] = [F.InvoiceLifecycleState, F.ReviewedBy, F.ReviewedAt];

export type SortKey = 'vendor' | 'po' | 'total' | 'approvalNeeded' | 'lifecycle' | 'recommendation' | 'updated';

export const TABLE_COLUMNS: { key: SortKey; label: string; field: FieldName; sortable: boolean }[] = [
  { key: 'vendor', label: 'Vendor', field: F.VendorName, sortable: true },
  { key: 'po', label: 'PO Number', field: F.PONumber, sortable: true },
  { key: 'total', label: 'Total', field: F.TotalAmount, sortable: true },
  { key: 'approvalNeeded', label: 'Approval required', field: F.ApprovalNeeded, sortable: true },
  { key: 'lifecycle', label: 'Lifecycle State', field: F.InvoiceLifecycleState, sortable: true },
  { key: 'recommendation', label: 'Recommendation', field: F.AgentRecommendation, sortable: true },
  { key: 'updated', label: 'Updated', field: F.UpdateTime, sortable: true },
];

export const LIFECYCLE = {
  EXTRACTED: 'EXTRACTED',
  HOLD_PO_MISMATCH: 'HOLD_PO_MISMATCH',
  AUTO_APPROVED: 'AUTO_APPROVED',
  NEEDS_AP_REVIEW: 'NEEDS_AP_REVIEW',
  READY_FOR_APPROVAL: 'READY_FOR_APPROVAL',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  POSTED: 'POSTED',
} as const;

export const PENDING_REVIEW_STATES: string[] = [LIFECYCLE.NEEDS_AP_REVIEW, LIFECYCLE.READY_FOR_APPROVAL];
export const RECOMMENDED_FOR_APPROVAL = LIFECYCLE.READY_FOR_APPROVAL;
