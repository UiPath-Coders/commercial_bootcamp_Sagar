import { useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronRight, CircleAlert } from 'lucide-react';
import { APPROVAL_INPUT_FIELDS } from '@/data/invoiceFields';
import { formatMoney, prettyJson, str, type Invoice } from '@/data/invoiceModel';

/**
 * ApprovalPackageJson as a reviewer reads it: the agent narrative, an evidence
 * checklist of the seven approval inputs (missing ones highlighted), a PO-match
 * summary, the reviewer note, and the raw JSON behind a collapsed toggle.
 * Tolerant of package shapes: participants' agents name keys differently.
 */
export function ApprovalPackageView({ invoice, packageText }: { invoice: Invoice; packageText: string }) {
  const [showRaw, setShowRaw] = useState(false);
  const pkg = parsePackage(packageText);
  const pretty = prettyJson(packageText);

  const narrative = narrativeText(pkg);
  const missing = missingFields(invoice.missingApprovalFields, pkg);
  const evidence = (pick(pkg, 'evidence') as Record<string, unknown> | undefined) ?? {};
  const po = (pick(pkg, 'poMatch', 'po_match', 'po') as Record<string, unknown> | undefined) ?? {};
  const matched = boolish(pick(po, 'poMatched', 'matched', 'po_matched')) ?? invoice.poMatched;
  const openAmount = pick(po, 'openAmount', 'open_amount', 'poOpenAmount', 'remainingAmount');
  const poReason = str(pick(po, 'reason', 'matchReason', 'message', 'detail') ?? '');
  const reviewerNote = str(pick(pkg, 'reviewerNote', 'reviewer_note') ?? '');
  const riskFlags = narrativeFlags(pkg);

  return (
    <div className="pkg">
      {pkg == null && packageText.trim() !== '' && <p className="pkg-muted">The package is plain text, not JSON. Open the raw view below.</p>}

      <section>
        <h4>Agent narrative</h4>
        {narrative ? <p className="pkg-narrative">{narrative}</p> : <p className="pkg-muted">No narrative. The agent writes one only when all approval evidence is present.</p>}
        {riskFlags.length > 0 && (
          <ul className="pkg-flags">
            {riskFlags.map((f) => (
              <li key={f}>
                <CircleAlert size={12} aria-hidden /> {f}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h4>Evidence checklist</h4>
        <ul className="pkg-checklist">
          {APPROVAL_INPUT_FIELDS.map((f) => {
            const value = str(invoice.raw[f] ?? pick(evidence, lowerFirst(f), f));
            const isMissing = missing.has(f.toLowerCase()) || value.trim() === '';
            return (
              <li key={f} className={isMissing ? 'is-missing' : ''}>
                {isMissing ? <CircleAlert size={14} aria-label="Missing" /> : <CheckCircle2 size={14} aria-label="Present" />}
                <span className="pkg-label">{spaced(f)}</span>
                <span className="pkg-value">{isMissing ? 'Missing' : value}</span>
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <h4>PO match</h4>
        <dl className="kv">
          <dt>Matched</dt>
          <dd>{matched == null ? '—' : matched ? 'Yes' : 'No'}</dd>
          <dt>Open amount</dt>
          <dd className="mono">{typeof openAmount === 'number' || (typeof openAmount === 'string' && openAmount.trim() !== '') ? formatMoney(Number(openAmount), invoice.currency) : '—'}</dd>
          <dt>Reason</dt>
          <dd>{poReason || (matched === true ? 'PO number and amount match the open purchase order.' : matched === false ? 'The PO did not match.' : '—')}</dd>
        </dl>
      </section>

      {reviewerNote && (
        <section>
          <h4>Reviewer note</h4>
          <p className="pkg-narrative">{reviewerNote}</p>
        </section>
      )}

      {packageText.trim() !== '' && (
        <div>
          <button type="button" className="pkg-raw-toggle" onClick={() => setShowRaw((v) => !v)} aria-expanded={showRaw}>
            {showRaw ? <ChevronDown size={12} aria-hidden /> : <ChevronRight size={12} aria-hidden />} View raw JSON
          </button>
          {showRaw && <pre className="json">{pretty ?? packageText}</pre>}
        </div>
      )}
    </div>
  );
}

function parsePackage(text: string): Record<string, unknown> | null {
  if (!text.trim()) return null;
  try {
    const v = JSON.parse(text);
    return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function pick(obj: unknown, ...keys: string[]): unknown {
  if (!obj || typeof obj !== 'object') return undefined;
  const o = obj as Record<string, unknown>;
  for (const k of keys) if (o[k] != null) return o[k];
  return undefined;
}

function boolish(v: unknown): boolean | null {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.toLowerCase() === 'true' ? true : v.toLowerCase() === 'false' ? false : null;
  return null;
}

function narrativeText(pkg: Record<string, unknown> | null): string {
  const n = pick(pkg, 'narrative', 'summary', 'agentNarrative');
  if (typeof n === 'string') return n;
  return str(pick(n, 'summary', 'text', 'narrative') ?? '');
}

function narrativeFlags(pkg: Record<string, unknown> | null): string[] {
  const flags = pick(pick(pkg, 'narrative'), 'risk_flags', 'riskFlags');
  return Array.isArray(flags) ? flags.map((f) => str(f)).filter(Boolean) : [];
}

function missingFields(recordValue: string, pkg: Record<string, unknown> | null): Set<string> {
  const fromPkg = pick(pick(pkg, 'decision'), 'missingApprovalFields');
  const list = Array.isArray(fromPkg) ? fromPkg.map((f) => str(f)) : [];
  recordValue
    .split(/[,;|\s]+/)
    .map((s) => s.replace(/[[\]"']/g, '').trim())
    .filter(Boolean)
    .forEach((s) => list.push(s));
  return new Set(list.map((s) => s.toLowerCase()));
}

const lowerFirst = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

/** GLAccount -> "GL Account", ReceiptReference -> "Receipt Reference" */
function spaced(field: string): string {
  return field.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
}
