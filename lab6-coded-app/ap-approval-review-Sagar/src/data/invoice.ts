import type { EntityRecord } from '@uipath/uipath-typescript/entities';
import { F, LIFECYCLE } from './fields';

/** Typed view over an AP_Invoice_Sagar record. Every field is optional. */
export interface Invoice {
  id: string;
  /** The raw record, so the detail panel can show every field verbatim. */
  raw: Record<string, unknown>;

  vendorName: string;
  vendorTaxId: string;
  invoiceNumber: string;
  invoiceDate: Date | null;
  poNumber: string;
  totalAmount: number | null;
  currency: string;
  dueDate: Date | null;
  processedTimestamp: Date | null;

  poMatched: boolean | null;
  approvalNeeded: boolean | null;
  postedToERP: boolean | null;

  approvalEvidenceState: string;
  missingApprovalFields: string;
  agentRecommendation: string;
  approvalPackageJson: string;
  agentProcessedAt: Date | null;
  lifecycleState: string;

  reviewedBy: string;
  reviewedAt: Date | null;

  createTime: Date | null;
  updateTime: Date | null;
}

export const str = (v: unknown): string => (typeof v === 'string' ? v : v == null ? '' : String(v));

export const num = (v: unknown): number | null => {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
};

export const bool = (v: unknown): boolean | null => {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    if (s === 'true') return true;
    if (s === 'false') return false;
  }
  return null;
};

export const date = (v: unknown): Date | null => {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v;
  if (typeof v !== 'string' || !v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
};

/** "No data" for coverage purposes. */
export function isEmptyValue(v: unknown): boolean {
  return v == null || (typeof v === 'string' && v.trim() === '');
}

/**
 * Large text fields can come back from list reads as a size marker
 * ("HasValue=true Length=N ...") instead of the content. Never render or
 * write that marker back; read the record by id for the real value.
 */
export function isSizeMarker(v: unknown): boolean {
  return typeof v === 'string' && /^HasValue=(true|false)\s+Length=\d+/i.test(v.trim());
}

export function toInvoice(record: EntityRecord): Invoice {
  const r = record as Record<string, unknown>;
  return {
    id: str(r[F.Id]),
    raw: r,
    vendorName: str(r[F.VendorName]),
    vendorTaxId: str(r[F.VendorTaxId]),
    invoiceNumber: str(r[F.InvoiceNumber]),
    invoiceDate: date(r[F.InvoiceDate]),
    poNumber: str(r[F.PONumber]),
    totalAmount: num(r[F.TotalAmount]),
    currency: str(r[F.Currency]),
    dueDate: date(r[F.DueDate]),
    processedTimestamp: date(r[F.ProcessedTimestamp]),
    poMatched: bool(r[F.POMatched]),
    approvalNeeded: bool(r[F.ApprovalNeeded]),
    // An unset PostedToERP means "not posted yet".
    postedToERP: bool(r[F.PostedToERP]) ?? false,
    approvalEvidenceState: str(r[F.ApprovalEvidenceState]),
    missingApprovalFields: str(r[F.MissingApprovalFields]),
    agentRecommendation: str(r[F.AgentRecommendation]),
    approvalPackageJson: str(r[F.ApprovalPackageJson]),
    agentProcessedAt: date(r[F.AgentProcessedAt]),
    lifecycleState: str(r[F.InvoiceLifecycleState]),
    reviewedBy: str(r[F.ReviewedBy]),
    reviewedAt: date(r[F.ReviewedAt]),
    createTime: date(r[F.CreateTime]),
    updateTime: date(r[F.UpdateTime]),
  };
}

/** Merge a write (payload + response) into an existing row without a full reload. */
export function mergeInvoice(existing: Invoice, patch: Record<string, unknown>): Invoice {
  return toInvoice({ ...existing.raw, ...patch, Id: existing.id } as EntityRecord);
}

// ---------------------------------------------------------------------------
// Decision rules
// ---------------------------------------------------------------------------

export type DecisionKind = 'approve' | 'reject';

export interface DecisionAvailability {
  canDecide: boolean;
  /** One-line note for the decision area: incomplete evidence, or why no action is available. */
  note: string | null;
}

/**
 * Approve / Reject are enabled only when InvoiceLifecycleState is
 * READY_FOR_APPROVAL or NEEDS_AP_REVIEW and ApprovalNeeded is true.
 * Every other state shows the decision area read-only with a reason.
 */
export function decisionAvailability(inv: Invoice, opts: { schemaOk: boolean; hasReviewer: boolean }): DecisionAvailability {
  const state = inv.lifecycleState;
  const reviewable = state === LIFECYCLE.READY_FOR_APPROVAL || state === LIFECYCLE.NEEDS_AP_REVIEW;

  if (reviewable && !opts.schemaOk) {
    return { canDecide: false, note: 'The entity is missing InvoiceLifecycleState, ReviewedBy or ReviewedAt, so a decision cannot be saved.' };
  }
  if (reviewable && !opts.hasReviewer) {
    return { canDecide: false, note: 'Your signed-in email could not be resolved, so ReviewedBy cannot be recorded. Sign out and sign in again.' };
  }

  switch (state) {
    case LIFECYCLE.READY_FOR_APPROVAL:
      if (inv.approvalNeeded !== true) {
        return { canDecide: false, note: 'READY_FOR_APPROVAL but ApprovalNeeded is not true, so there is nothing to approve. Rerun the approval agent on this record.' };
      }
      return { canDecide: true, note: null };
    case LIFECYCLE.NEEDS_AP_REVIEW:
      if (inv.approvalNeeded !== true) {
        return { canDecide: false, note: 'NEEDS_AP_REVIEW but ApprovalNeeded is not true, so there is nothing to approve. Rerun the approval agent on this record.' };
      }
      return {
        canDecide: true,
        note: `Approval evidence is incomplete${inv.missingApprovalFields ? `: missing ${inv.missingApprovalFields}` : ''}.`,
      };
    case LIFECYCLE.AUTO_APPROVED:
      return { canDecide: false, note: 'Auto-approved by the approval agent (PO matched, no approval needed). No human decision is required.' };
    case LIFECYCLE.HOLD_PO_MISMATCH:
      return { canDecide: false, note: 'On hold because the PO did not match. Resolve the mismatch upstream; reviewers do not decide this state.' };
    case LIFECYCLE.APPROVED:
      return { canDecide: false, note: `Already approved${inv.reviewedBy ? ` by ${inv.reviewedBy}` : ''}. It is now ready to post to the ERP.` };
    case LIFECYCLE.REJECTED:
      return { canDecide: false, note: `Already rejected${inv.reviewedBy ? ` by ${inv.reviewedBy}` : ''}. The process has ended for this invoice.` };
    case LIFECYCLE.POSTED:
      return { canDecide: false, note: 'Already posted to the ERP. Nothing is left to decide.' };
    case LIFECYCLE.EXTRACTED:
      return { canDecide: false, note: 'Extracted, but the approval agent has not prepared it yet. Run the agent on this record first.' };
    case '':
      return { canDecide: false, note: 'No lifecycle state yet. Run the approval agent on this record first.' };
    default:
      return { canDecide: false, note: `Unknown lifecycle state "${state}". Only NEEDS_AP_REVIEW and READY_FOR_APPROVAL can be decided.` };
  }
}

// ---------------------------------------------------------------------------
// "Approval required" column
// ---------------------------------------------------------------------------

const APPROVAL_OPEN_STATES = new Set<string>(['', LIFECYCLE.EXTRACTED, LIFECYCLE.NEEDS_AP_REVIEW, LIFECYCLE.READY_FOR_APPROVAL]);
const APPROVAL_DECIDED_WORDS: Record<string, string> = {
  [LIFECYCLE.APPROVED]: 'Approved',
  [LIFECYCLE.REJECTED]: 'Rejected',
  [LIFECYCLE.POSTED]: 'Posted',
};

/** Amber "Needed" while the approval is outstanding; a neutral decision word once decided; otherwise null (dash). */
export function approvalPill(inv: Pick<Invoice, 'approvalNeeded' | 'lifecycleState'>): { tone: 'needed' | 'decided'; text: string } | null {
  if (inv.approvalNeeded !== true) return null;
  const decided = APPROVAL_DECIDED_WORDS[inv.lifecycleState];
  if (decided) return { tone: 'decided', text: decided };
  if (APPROVAL_OPEN_STATES.has(inv.lifecycleState)) return { tone: 'needed', text: 'Needed' };
  return null;
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

export function formatMoney(amount: number | null, currency: string): string {
  if (amount == null) return '—';
  const n = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
  return currency ? `${n} ${currency}` : n;
}

export function formatDateTime(d: Date | null): string {
  if (!d) return '—';
  return d.toISOString().replace('T', ' ').replace(/:\d{2}\.\d{3}Z$/, 'Z');
}

export function formatDate(d: Date | null): string {
  if (!d) return '—';
  return d.toISOString().slice(0, 10);
}

export function initials(name: string): string {
  const parts = name.replace(/[^\p{L}\p{N}\s]/gu, ' ').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function prettyJson(text: string): string | null {
  if (!text.trim()) return null;
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return null;
  }
}

/** GLAccount -> "GL Account", ReceiptReference -> "Receipt Reference" */
export function spaced(field: string): string {
  return field.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
}

export function isEvaluationRow(invoiceNumber: string | null | undefined): boolean {
  return (invoiceNumber ?? '').trim().toUpperCase().startsWith('TRAIN-');
}
