import { useEffect, useState } from 'react';
import { Check, CheckCircle2, Copy, Info, LoaderCircle, X } from 'lucide-react';
import { APPROVAL_INPUT_FIELDS, F, type FieldName } from '@/data/invoiceFields';
import {
  decisionAvailability,
  formatDate,
  formatDateTime,
  formatMoney,
  initials,
  isSizeMarker,
  str,
  type Invoice,
} from '@/data/invoiceModel';
import type { DecisionState } from '@/data/useReviewDecision';
import type { SchemaState } from '@/data/schema';
import { fieldMissing } from '@/data/schema';
import { ErrorBanner } from './StateViews';
import { ApprovalPackageView } from './ApprovalPackageView';
import { EvaluationTag, isEvaluationRow } from './EvaluationTag';

/**
 * Slide-over with every field on the record, grouped, plus the human decision.
 * On open it re-reads the record by id so ApprovalPackageJson shows its full
 * content (list reads return a size marker for MULTILINE_MAX fields).
 */
export function InvoiceDetailPanel({
  invoice,
  schema,
  decision,
  reviewerEmail,
  onClose,
  onUpdated,
  onSignIn,
}: {
  invoice: Invoice;
  schema: SchemaState;
  decision: DecisionState;
  reviewerEmail: string | null;
  onClose: () => void;
  onUpdated: (next: Invoice) => void;
  onSignIn: () => void;
}) {
  const [full, setFull] = useState<Invoice>(invoice);
  const [refreshing, setRefreshing] = useState(false);
  // Approve and Reject both go through a confirmation that names the exact InvoiceNumber and VendorName,
  // because evaluation rows (TRAIN-*) share vendors with real invoices.
  const [confirming, setConfirming] = useState<'approve' | 'reject' | null>(null);
  const [reason, setReason] = useState('');
  const [saved, setSaved] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Keep in sync when the parent row changes (after a write) and refetch the full record on open.
  useEffect(() => {
    setFull(invoice);
    setSaved(null);
    setWarning(null);
    setConfirming(null);
    setReason('');
    decision.clearError();
    let cancelled = false;
    if (isSizeMarker(invoice.approvalPackageJson) || !invoice.approvalPackageJson) {
      setRefreshing(true);
      decision
        .fetchFull(invoice.id)
        .then((f) => {
          if (!cancelled) setFull(f);
        })
        .catch(() => {
          /* keep the list-read copy; the panel notes the marker */
        })
        .finally(() => {
          if (!cancelled) setRefreshing(false);
        });
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const availability = decisionAvailability(full, { schemaOk: schema.canWriteDecision, hasReviewer: Boolean(reviewerEmail) });
  const busy = decision.saving != null;

  const approve = async () => {
    const result = await decision.approve(full);
    if (result) {
      setFull(result.invoice);
      onUpdated(result.invoice);
      setSaved('Approved. The record now satisfies the Lab 4 ready-to-post rule.');
      setWarning(result.warning);
      setConfirming(null);
    }
  };

  const reject = async () => {
    const result = await decision.reject(full, reason);
    if (result) {
      setFull(result.invoice);
      onUpdated(result.invoice);
      setSaved('Rejected. The process ended for this invoice.');
      setWarning(result.warning);
      setConfirming(null);
    }
  };

  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(full.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      /* ignore */
    }
  };

  const packageText = isSizeMarker(full.approvalPackageJson) ? '' : full.approvalPackageJson;

  return (
    <>
      <div className="panel-backdrop" onClick={onClose} aria-hidden />
      <aside className="panel" role="dialog" aria-modal="true" aria-labelledby="panel-title">
        <header className="panel-head">
          <div className="vendor-cell">
            <span className="avatar" aria-hidden>
              {initials(full.vendorName || full.invoiceNumber)}
            </span>
            <div className="vendor-text">
              <h2 id="panel-title" className="vendor-name" title={full.vendorName}>
                {full.vendorName || 'Unknown vendor'}
              </h2>
              <span className="vendor-sub">
                {full.invoiceNumber || '—'} <EvaluationTag invoiceNumber={full.invoiceNumber} />
              </span>
              <span className="panel-id">
                <code title={full.id}>{full.id}</code>
                <button className="btn-icon" style={{ width: 24, height: 24, minHeight: 24 }} onClick={copyId} title={copied ? 'Copied' : 'Copy record Id'} aria-label="Copy record Id">
                  {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
                </button>
              </span>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose} title="Close" aria-label="Close panel">
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="panel-body">
          <Group title="Invoice">
            <Row label="Invoice Number" field={F.InvoiceNumber} value={full.invoiceNumber} mono schema={schema} />
            <Row label="Invoice Date" field={F.InvoiceDate} value={formatDate(full.invoiceDate)} mono schema={schema} empty={!full.invoiceDate} />
            <Row label="Due Date" field={F.DueDate} value={formatDate(full.dueDate)} mono schema={schema} empty={!full.dueDate} />
            <Row label="Total" field={F.TotalAmount} value={formatMoney(full.totalAmount, full.currency)} mono schema={schema} empty={full.totalAmount == null} />
            <Row label="Currency" field={F.Currency} value={full.currency} mono schema={schema} />
            <Row label="Vendor Tax ID" field={F.VendorTaxId} value={full.vendorTaxId} mono schema={schema} />
            <Row label="Processed" field={F.ProcessedTimestamp} value={formatDateTime(full.processedTimestamp)} mono schema={schema} empty={!full.processedTimestamp} />
          </Group>

          <Group title="PO match">
            <Row label="PO Number" field={F.PONumber} value={full.poNumber} mono schema={schema} />
            <Row label="PO Matched" field={F.POMatched} value={boolText(full.poMatched)} schema={schema} empty={full.poMatched == null} />
            <Row label="Approval Required" field={F.ApprovalNeeded} value={boolText(full.approvalNeeded)} schema={schema} empty={full.approvalNeeded == null} />
            <Row label="Posted To ERP" field={F.PostedToERP} value={boolText(full.postedToERP)} schema={schema} empty={full.postedToERP == null} />
          </Group>

          <Group title="Approval evidence">
            {APPROVAL_INPUT_FIELDS.map((f) => (
              <Row key={f} label={spaced(f)} field={f} value={str(full.raw[f])} schema={schema} />
            ))}
          </Group>

          <Group title="Agent package" trailing={refreshing ? <LoaderCircle size={12} className="spin" aria-label="Refreshing full record" /> : null}>
            <Row label="Evidence State" field={F.ApprovalEvidenceState} value={full.approvalEvidenceState} mono schema={schema} />
            <Row label="Missing Fields" field={F.MissingApprovalFields} value={full.missingApprovalFields} mono schema={schema} />
            <Row label="Recommendation" field={F.AgentRecommendation} value={full.agentRecommendation} mono schema={schema} />
            <Row label="Agent Processed At" field={F.AgentProcessedAt} value={formatDateTime(full.agentProcessedAt)} mono schema={schema} empty={!full.agentProcessedAt} />
            <div style={{ gridColumn: '1 / -1' }}>
              <div className="kv" style={{ marginBottom: 4 }}>
                <dt>Approval Package</dt>
                <dd className={packageText ? '' : 'is-empty'}>
                  {fieldMissing(schema, F.ApprovalPackageJson)
                    ? absent(F.ApprovalPackageJson)
                    : packageText
                      ? ''
                      : isSizeMarker(full.approvalPackageJson)
                        ? 'Stored, full content unavailable in this view'
                        : '—'}
                </dd>
              </div>
              {packageText && !fieldMissing(schema, F.ApprovalPackageJson) ? <ApprovalPackageView invoice={full} packageText={packageText} /> : null}
            </div>
          </Group>

          <Group title="Review decision">
            <Row label="Lifecycle State" field={F.InvoiceLifecycleState} value={full.lifecycleState} mono schema={schema} />
            <Row label="Reviewed By" field={F.ReviewedBy} value={full.reviewedBy} mono schema={schema} />
            <Row label="Reviewed At" field={F.ReviewedAt} value={formatDateTime(full.reviewedAt)} mono schema={schema} empty={!full.reviewedAt} />
          </Group>
        </div>

        <footer className="panel-foot">
          {decision.error && <ErrorBanner error={decision.error} compact={decision.error.kind !== 'auth'} onSignIn={onSignIn} onRetry={decision.error.kind === 'auth' ? undefined : () => decision.clearError()} />}
          {warning && (
            <div className="banner">
              <Info size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
              <div className="banner-body">{warning}</div>
            </div>
          )}
          {saved && (
            <div className="decision-saved" role="status">
              <CheckCircle2 size={16} aria-hidden /> {saved}
            </div>
          )}

          {!saved && availability.reason && (
            <div className="decision-reason">
              <Info size={14} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
              <span>{availability.reason}</span>
            </div>
          )}

          {!saved && confirming ? (
            <form
              className="reject-form confirm-box"
              role="alertdialog"
              aria-labelledby="confirm-title"
              onSubmit={(e) => {
                e.preventDefault();
                if (busy) return;
                if (confirming === 'approve') approve();
                else reject();
              }}
            >
              <p id="confirm-title" className="confirm-title">
                {confirming === 'approve' ? 'Approve' : 'Reject'} invoice <strong className="mono">{full.invoiceNumber || '—'}</strong> from{' '}
                <strong>{full.vendorName || 'Unknown vendor'}</strong>?
              </p>
              {isEvaluationRow(full.invoiceNumber) && (
                <div className="decision-reason">
                  <Info size={14} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>This is a Lab 5 evaluation row, not a vendor invoice. Check the invoice number before you confirm.</span>
                </div>
              )}
              {confirming === 'reject' && (
                <>
                  <label htmlFor="reject-reason">Reason for rejection (one line, stored as reviewerNote)</label>
                  <input id="reject-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Amount exceeds PO open balance" maxLength={240} autoFocus required disabled={busy} />
                </>
              )}
              <div className="decision-row">
                {confirming === 'approve' ? (
                  <button type="submit" className="btn btn-primary" disabled={busy} autoFocus>
                    {decision.saving === 'approve' ? <LoaderCircle size={14} className="spin" aria-hidden /> : <Check size={14} aria-hidden />} Confirm approve
                  </button>
                ) : (
                  <button type="submit" className="btn btn-danger-outline" disabled={busy || reason.trim() === ''}>
                    {decision.saving === 'reject' ? <LoaderCircle size={14} className="spin" aria-hidden /> : null} Confirm reject
                  </button>
                )}
                <button type="button" className="btn btn-secondary" onClick={() => setConfirming(null)} disabled={busy}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            !saved && (
              <div className="decision-row">
                <button className="btn btn-primary" onClick={() => setConfirming('approve')} disabled={!availability.canApprove || busy} title={availability.canApprove ? 'Set InvoiceLifecycleState = APPROVED' : availability.reason ?? undefined}>
                  {decision.saving === 'approve' ? <LoaderCircle size={14} className="spin" aria-hidden /> : <Check size={14} aria-hidden />} Approve
                </button>
                <button className="btn btn-danger-outline" onClick={() => setConfirming('reject')} disabled={!availability.canReject || busy} title={availability.canReject ? 'Set InvoiceLifecycleState = REJECTED' : availability.reason ?? undefined}>
                  <X size={14} aria-hidden /> Reject
                </button>
                {reviewerEmail && (availability.canApprove || availability.canReject) && (
                  <span className="decision-reason" style={{ marginLeft: 'auto' }}>
                    Recorded as <code>{reviewerEmail}</code>
                  </span>
                )}
              </div>
            )
          )}
        </footer>
      </aside>
    </>
  );
}

function Group({ title, children, trailing }: { title: string; children: React.ReactNode; trailing?: React.ReactNode }) {
  return (
    <section className="group">
      <h3>
        {title} {trailing}
      </h3>
      <dl className="kv">{children}</dl>
    </section>
  );
}

function Row({ label, field, value, mono, schema, empty }: { label: string; field: FieldName; value: string; mono?: boolean; schema: SchemaState; empty?: boolean }) {
  const missing = fieldMissing(schema, field);
  const isEmpty = empty ?? (value === '' || value === '—');
  return (
    <>
      <dt title={field}>{label}</dt>
      <dd className={`${mono ? 'mono' : ''} ${missing ? 'is-absent' : isEmpty ? 'is-empty' : ''}`.trim()}>{missing ? absent(field) : isEmpty ? '—' : value}</dd>
    </>
  );
}

function absent(field: string) {
  return `Field ${field} is not in the schema`;
}

function boolText(v: boolean | null): string {
  return v == null ? '—' : v ? 'Yes' : 'No';
}

/** GLAccount -> "GL Account", ReceiptReference -> "Receipt Reference" */
function spaced(field: string): string {
  return field.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
}
