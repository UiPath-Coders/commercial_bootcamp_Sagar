import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Check, CheckCircle2, Copy, Info, LoaderCircle, Lock, X } from 'lucide-react';
import { APPROVAL_INPUT_FIELDS, F } from '@/data/fields';
import { decisionAvailability, formatDate, formatDateTime, formatMoney, initials, isEvaluationRow, isSizeMarker, spaced, str, type DecisionKind, type Invoice } from '@/data/invoice';
import type { DecisionState } from '@/data/useDecision';
import { fieldMissing, type SchemaState } from '@/data/useSchema';
import { ErrorBanner } from './StateViews';
import { ApprovalPackageView } from './ApprovalPackageView';
import { EvaluationTag } from './EvaluationTag';

/**
 * Slide-over with every field on the record, grouped, plus the human decision.
 * On open it re-reads the record by id so ApprovalPackageJson has its full content.
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
  const [confirming, setConfirming] = useState<DecisionKind | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  const { clearError, fetchFull } = decision;

  // Reset per record and refetch the full record on open.
  useEffect(() => {
    setFull(invoice);
    setSaved(null);
    setWarning(null);
    setConfirming(null);
    clearError();
    panelRef.current?.focus();
    let cancelled = false;
    setRefreshing(true);
    fetchFull(invoice.id)
      .then((f) => {
        if (!cancelled) setFull(f);
      })
      .catch(() => {
        /* keep the list-read copy */
      })
      .finally(() => {
        if (!cancelled) setRefreshing(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || decision.saving) return;
      if (confirming) setConfirming(null);
      else onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, confirming, decision.saving]);

  const availability = decisionAvailability(full, { schemaOk: schema.canWriteDecision, hasReviewer: Boolean(reviewerEmail) });
  const busy = decision.saving != null;

  const submit = async (kind: DecisionKind, reason?: string) => {
    const result = await decision.decide(full, kind, reason);
    if (result) {
      setFull(result.invoice);
      onUpdated(result.invoice);
      setSaved(kind === 'approve' ? `Approved. InvoiceLifecycleState is now APPROVED.` : `Rejected. InvoiceLifecycleState is now REJECTED.`);
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
      /* clipboard unavailable */
    }
  };

  const packageText = isSizeMarker(full.approvalPackageJson) ? '' : full.approvalPackageJson;
  const packageMissing = fieldMissing(schema, F.ApprovalPackageJson);

  return (
    <>
      <div className="panel-backdrop" onClick={() => !busy && onClose()} aria-hidden />
      <aside ref={panelRef} tabIndex={-1} className="panel" role="dialog" aria-modal="true" aria-labelledby="panel-title">
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
                {full.invoiceNumber || '—'}
                <EvaluationTag invoiceNumber={full.invoiceNumber} />
              </span>
              <span className="panel-id">
                <span className="panel-id-label">Record ID</span>
                <code title={full.id}>{full.id}</code>
                <button type="button" className="btn-icon btn-icon-xs" onClick={copyId} title={copied ? 'Copied' : 'Copy record ID'} aria-label={copied ? 'Record ID copied' : 'Copy record ID'}>
                  {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
                </button>
              </span>
            </div>
          </div>
          <button type="button" className="btn-icon" onClick={onClose} disabled={busy} title="Close" aria-label="Close invoice details">
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="panel-body">
          <Group title="Invoice">
            <Row label="Invoice Number" field={F.InvoiceNumber} value={full.invoiceNumber} mono schema={schema} />
            <Row label="Vendor Name" field={F.VendorName} value={full.vendorName} schema={schema} />
            <Row label="Vendor Tax ID" field={F.VendorTaxId} value={full.vendorTaxId} mono schema={schema} />
            <Row label="Invoice Date" field={F.InvoiceDate} value={formatDate(full.invoiceDate)} mono schema={schema} empty={!full.invoiceDate} />
            <Row label="Due Date" field={F.DueDate} value={formatDate(full.dueDate)} mono schema={schema} empty={!full.dueDate} />
            <Row label="Total Amount" field={F.TotalAmount} value={formatMoney(full.totalAmount, '')} mono schema={schema} empty={full.totalAmount == null} />
            <Row label="Currency" field={F.Currency} value={full.currency} mono schema={schema} />
            <Row label="Processed" field={F.ProcessedTimestamp} value={formatDateTime(full.processedTimestamp)} mono schema={schema} empty={!full.processedTimestamp} />
            <Row label="Created" field={F.CreateTime} value={formatDateTime(full.createTime)} mono schema={schema} empty={!full.createTime} />
            <Row label="Updated" field={F.UpdateTime} value={formatDateTime(full.updateTime)} mono schema={schema} empty={!full.updateTime} />
          </Group>

          <Group title="PO match">
            <Row label="PO Number" field={F.PONumber} value={full.poNumber} mono schema={schema} />
            <Row label="PO Matched" field={F.POMatched} value={boolText(full.poMatched)} schema={schema} empty={full.poMatched == null} />
            <Row label="Approval Needed" field={F.ApprovalNeeded} value={boolText(full.approvalNeeded)} schema={schema} empty={full.approvalNeeded == null} />
            <Row label="Posted To ERP" field={F.PostedToERP} value={boolText(full.postedToERP)} schema={schema} empty={full.postedToERP == null} />
          </Group>

          <Group title="Approval evidence">
            {APPROVAL_INPUT_FIELDS.map((f) => (
              <Row key={f} label={spaced(f)} field={f} value={str(full.raw[f])} schema={schema} />
            ))}
          </Group>

          <Group title="Agent package" trailing={refreshing ? <LoaderCircle size={12} className="spin" aria-label="Loading the full record" /> : null}>
            <Row label="Evidence State" field={F.ApprovalEvidenceState} value={full.approvalEvidenceState} mono schema={schema} />
            <Row label="Missing Fields" field={F.MissingApprovalFields} value={full.missingApprovalFields} mono schema={schema} />
            <Row label="Recommendation" field={F.AgentRecommendation} value={full.agentRecommendation} mono schema={schema} />
            <Row label="Agent Processed At" field={F.AgentProcessedAt} value={formatDateTime(full.agentProcessedAt)} mono schema={schema} empty={!full.agentProcessedAt} />
            <dt title={F.ApprovalPackageJson}>Approval Package</dt>
            <dd className={packageMissing ? 'is-absent' : packageText ? '' : 'is-empty'}>
              {packageMissing ? absent(F.ApprovalPackageJson) : packageText ? 'Shown below' : isSizeMarker(full.approvalPackageJson) ? 'Stored, full content unavailable' : '—'}
            </dd>
          </Group>
          {packageText && !packageMissing && <ApprovalPackageView invoice={full} packageText={packageText} />}

          <Group title="Review decision">
            <Row label="Lifecycle State" field={F.InvoiceLifecycleState} value={full.lifecycleState} mono schema={schema} />
            <Row label="Reviewed By" field={F.ReviewedBy} value={full.reviewedBy} mono schema={schema} />
            <Row label="Reviewed At" field={F.ReviewedAt} value={formatDateTime(full.reviewedAt)} mono schema={schema} empty={!full.reviewedAt} />
          </Group>
        </div>

        <footer className="panel-foot" aria-label="Decision">
          {warning && (
            <div className="banner">
              <Info size={16} aria-hidden className="banner-icon" />
              <div className="banner-body">{warning}</div>
            </div>
          )}
          {saved ? (
            <div className="decision-saved" role="status">
              <CheckCircle2 size={16} aria-hidden /> {saved}
            </div>
          ) : availability.canDecide ? (
            <>
              {availability.note && (
                <div className="decision-note is-warn">
                  <Info size={14} aria-hidden className="banner-icon" />
                  <span>{availability.note}</span>
                </div>
              )}
              <div className="decision-row">
                <button type="button" className="btn btn-primary" onClick={() => setConfirming('approve')} disabled={busy} title="Set InvoiceLifecycleState to APPROVED">
                  <Check size={14} aria-hidden /> Approve
                </button>
                <button type="button" className="btn btn-danger-outline" onClick={() => setConfirming('reject')} disabled={busy} title="Set InvoiceLifecycleState to REJECTED">
                  <X size={14} aria-hidden /> Reject
                </button>
                {reviewerEmail && (
                  <span className="decision-note decision-who">
                    Recorded as <code>{reviewerEmail}</code>
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="decision-note" role="note">
              <Lock size={14} aria-hidden className="banner-icon" />
              <span>{availability.note ?? 'No action is available for this invoice.'}</span>
            </div>
          )}
        </footer>
      </aside>

      {confirming && (
        <ConfirmDialog
          kind={confirming}
          invoice={full}
          saving={decision.saving === confirming}
          error={decision.error}
          onCancel={() => {
            if (busy) return;
            clearError();
            setConfirming(null);
          }}
          onConfirm={(reason) => submit(confirming, reason)}
          onSignIn={onSignIn}
        />
      )}
    </>
  );
}

function ConfirmDialog({
  kind,
  invoice,
  saving,
  error,
  onCancel,
  onConfirm,
  onSignIn,
}: {
  kind: DecisionKind;
  invoice: Invoice;
  saving: boolean;
  error: DecisionState['error'];
  onCancel: () => void;
  onConfirm: (reason?: string) => void;
  onSignIn: () => void;
}) {
  const [reason, setReason] = useState('');
  const isReject = kind === 'reject';
  const canSubmit = !saving && (!isReject || reason.trim() !== '');
  const confirm = () => canSubmit && onConfirm(isReject ? reason.trim() : undefined);

  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <form
        className="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          confirm();
        }}
      >
        <h2 id="confirm-title">{isReject ? 'Reject invoice' : 'Approve invoice'}</h2>
        <p id="confirm-desc" className="confirm-title">
          {isReject ? 'Reject' : 'Approve'} invoice <strong className="mono">{invoice.invoiceNumber || '—'}</strong> from <strong>{invoice.vendorName || 'Unknown vendor'}</strong>?
        </p>
        {isEvaluationRow(invoice.invoiceNumber) && (
          <div className="decision-note">
            <Info size={14} aria-hidden className="banner-icon" />
            <span>This is Lab 5 evaluation data, not a vendor invoice. Check the invoice number before you confirm.</span>
          </div>
        )}
        {isReject && (
          <div className="field">
            <label htmlFor="reject-reason">Reason for rejection (one line, saved as reviewerNote)</label>
            <input
              id="reject-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Amount exceeds the PO open balance"
              maxLength={240}
              autoFocus
              required
              disabled={saving}
            />
          </div>
        )}
        {error && <ErrorBanner error={error} onSignIn={onSignIn} onRetry={canSubmit ? confirm : undefined} retryLabel={`Retry ${isReject ? 'reject' : 'approve'}`} />}
        <div className="decision-row dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          {isReject ? (
            <button type="submit" className="btn btn-danger-outline" disabled={!canSubmit}>
              {saving ? <LoaderCircle size={14} className="spin" aria-hidden /> : <X size={14} aria-hidden />} {saving ? 'Saving…' : 'Confirm reject'}
            </button>
          ) : (
            <button type="submit" className="btn btn-primary" disabled={!canSubmit} autoFocus>
              {saving ? <LoaderCircle size={14} className="spin" aria-hidden /> : <Check size={14} aria-hidden />} {saving ? 'Saving…' : 'Confirm approve'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function Group({ title, children, trailing }: { title: string; children: ReactNode; trailing?: ReactNode }) {
  return (
    <section className="field-group">
      <h3>
        {title} {trailing}
      </h3>
      <dl className="kv">{children}</dl>
    </section>
  );
}

function Row({ label, field, value, mono, schema, empty }: { label: string; field: string; value: string; mono?: boolean; schema: SchemaState; empty?: boolean }) {
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
