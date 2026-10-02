import type { EntityRecord } from '@uipath/uipath-typescript/entities';
import { F, LIFECYCLE } from './invoiceFields';

/**
 * Typed view over an AP_Invoice_<user_name> record.
 * Every field is optional: Day 1 records lack the Lab 5 columns, and the UI
 * distinguishes "no data" (null) from "field not in schema" (see schema.ts).
 */
export interface Invoice {
  id: string;
  /** The raw record, kept so the detail panel can show every field verbatim. */
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

/** True when a Data Fabric value should be treated as "no data" for coverage purposes. */
export function isEmptyValue(v: unknown): boolean {
  return v == null || (typeof v === 'string' && v.trim() === '');
}

/**
 * MULTILINE_MAX fields come back from list / query reads as a size marker
 * ("HasValue=true Length=N ...") instead of the content. Never render or
 * write that marker back; fetch the record by id for the real value.
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
    postedToERP: bool(r[F.PostedToERP]),
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

/** Merge a write response (or the payload we sent) into an existing row without a full reload. */
export function mergeInvoice(existing: Invoice, patch: Record<string, unknown>): Invoice {
  return toInvoice({ ...existing.raw, ...patch, Id: existing.id } as EntityRecord);
}

// ---------------------------------------------------------------------------
// Decision rules (the "Approved?" gateway)
// ---------------------------------------------------------------------------

export type DecisionKind = 'approve' | 'reject';

export interface DecisionAvailability {
  canApprove: boolean;
  canReject: boolean;
  /** One-line explanation shown when neither action (or only one) is available. */
  reason: string | null;
}

/**
 * Approve : NEEDS_AP_REVIEW | READY_FOR_APPROVAL -> APPROVED
 * Reject  : NEEDS_AP_REVIEW | READY_FOR_APPROVAL -> REJECTED
 * Both additionally require ApprovalNeeded = true (a record in a reviewable
 * state with ApprovalNeeded false is an agent inconsistency, not a decision).
 * On NEEDS_AP_REVIEW the panel shows a one-line note that the approval
 * evidence is incomplete (MissingApprovalFields); the reviewer still decides.
 */
export function decisionAvailability(inv: Invoice, opts: { schemaOk: boolean; hasReviewer: boolean }): DecisionAvailability {
  if (!opts.schemaOk) {
    return {
      canApprove: false,
      canReject: false,
      reason: 'The entity is missing InvoiceLifecycleState, ReviewedBy or ReviewedAt, so a decision cannot be written. Finish Lab 5 step 2 first.',
    };
  }
  if (!opts.hasReviewer) {
    return {
      canApprove: false,
      canReject: false,
      reason: 'Your signed-in email could not be resolved, so ReviewedBy cannot be recorded. Sign out and back in.',
    };
  }

  const state = inv.lifecycleState;
  switch (state) {
    case LIFECYCLE.READY_FOR_APPROVAL:
      if (inv.approvalNeeded !== true) {
        return { canApprove: false, canReject: false, reason: 'READY_FOR_APPROVAL but ApprovalNeeded is not true. Rerun the Lab 5 agent on this record.' };
      }
      return { canApprove: true, canReject: true, reason: null };
    case LIFECYCLE.NEEDS_AP_REVIEW:
      if (inv.approvalNeeded !== true) {
        return { canApprove: false, canReject: false, reason: 'NEEDS_AP_REVIEW but ApprovalNeeded is not true. Rerun the Lab 5 agent on this record.' };
      }
      return {
        canApprove: true,
        canReject: true,
        reason: `Approval evidence is incomplete${inv.missingApprovalFields ? ` (missing: ${inv.missingApprovalFields})` : ''}.`,
      };
    case LIFECYCLE.AUTO_APPROVED:
      return { canApprove: false, canReject: false, reason: 'Auto-approved by the Lab 5 agent (PO matched, under threshold). No human decision is needed; Lab 4 will post it.' };
    case LIFECYCLE.HOLD_PO_MISMATCH:
      return { canApprove: false, canReject: false, reason: 'On hold: the PO did not match. Resolve the mismatch upstream and rerun the Lab 5 agent; the reviewer does not decide this state.' };
    case LIFECYCLE.APPROVED:
      return { canApprove: false, canReject: false, reason: `Already approved${inv.reviewedBy ? ` by ${inv.reviewedBy}` : ''}. It now satisfies the Lab 4 ready-to-post rule.` };
    case LIFECYCLE.REJECTED:
      return { canApprove: false, canReject: false, reason: `Already rejected${inv.reviewedBy ? ` by ${inv.reviewedBy}` : ''}. The process ended for this invoice.` };
    case LIFECYCLE.POSTED:
      return { canApprove: false, canReject: false, reason: 'Already posted to the ERP. Nothing left to decide.' };
    case '':
      return { canApprove: false, canReject: false, reason: 'No InvoiceLifecycleState yet. Run the Lab 5 agent against this record first.' };
    default:
      return { canApprove: false, canReject: false, reason: `Unknown lifecycle state "${state}". Only NEEDS_AP_REVIEW and READY_FOR_APPROVAL can be decided.` };
  }
}

// ---------------------------------------------------------------------------
// "Approval required" column
// ---------------------------------------------------------------------------

/** States in which an approval is still outstanding (empty = not yet classified). */
const APPROVAL_OPEN_STATES = new Set<string>(['', 'EXTRACTED', LIFECYCLE.NEEDS_AP_REVIEW, LIFECYCLE.READY_FOR_APPROVAL]);
const APPROVAL_DECIDED_WORDS: Record<string, string> = {
  [LIFECYCLE.APPROVED]: 'Approved',
  [LIFECYCLE.REJECTED]: 'Rejected',
  [LIFECYCLE.POSTED]: 'Posted',
};

/**
 * Amber "Needed" only while the approval is outstanding; once a reviewer has
 * decided (or the invoice posted) show the decision word in a neutral pill so
 * a done row no longer reads as "not done". Rows that never needed approval show a dash.
 */
export function approvalPill(inv: Pick<Invoice, 'approvalNeeded' | 'lifecycleState'>): { tone: 'needed' | 'decided'; text: string } | null {
  if (inv.approvalNeeded !== true) return null;
  const decided = APPROVAL_DECIDED_WORDS[inv.lifecycleState];
  if (decided) return { tone: 'decided', text: decided };
  if (APPROVAL_OPEN_STATES.has(inv.lifecycleState)) return { tone: 'needed', text: 'Needed' };
  return null;
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

export function formatMoney(amount: number | null, currency: string): string {
  if (amount == null) return '—';
  const code = currency && /^[A-Z]{3}$/.test(currency) ? currency : undefined;
  try {
    return new Intl.NumberFormat('en-US', code ? { style: 'currency', currency: code } : { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`.trim();
  }
}

export function formatDateTime(d: Date | null): string {
  if (!d) return '—';
  return d.toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, 'Z');
}

export function formatDate(d: Date | null): string {
  if (!d) return '—';
  return d.toISOString().slice(0, 10);
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

/** Pretty-print JSON text; returns null when the text is not valid JSON. */
export function prettyJson(text: string): string | null {
  if (!text.trim()) return null;
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return null;
  }
}
