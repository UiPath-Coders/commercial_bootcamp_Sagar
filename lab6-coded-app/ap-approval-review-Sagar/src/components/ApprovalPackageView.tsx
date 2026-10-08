import { useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronRight, CircleAlert } from 'lucide-react';
import { APPROVAL_INPUT_FIELDS } from '@/data/fields';
import { formatMoney, prettyJson, spaced, str, type Invoice } from '@/data/invoice';

/**
 * ApprovalPackageJson as a reviewer reads it: the agent narrative, an evidence
 * checklist of the seven approval inputs (MissingApprovalFields highlighted),
 * a PO-match summary, the reviewer note, and the raw JSON behind a collapsed toggle.
 * Tolerant of package shapes: key names vary between agents.
 */
export function ApprovalPackageView({ invoice, packageText }: { invoice: Invoice; packageText: string }) {
  const [showRaw, setShowRaw] = useState(false);
  const pkg = parsePackage(packageText);
  const pretty = prettyJson(packageText);

  const narrative = narrativeText(pkg);
  const riskFlags = narrativeFlags(pkg);
  const missing = missingFields(invoice.missingApprovalFields, pkg);
  const evidence = asObject(pick(pkg, 'evidence', 'approvalEvidence', 'approval_evidence'));
  const po = asObject(pick(pkg, 'poMatch', 'po_match', 'po'));
  const openAmount = pick(po, 'openAmount', 'open_amount', 'poOpenAmount', 'remainingAmount');
  const poReason = str(pick(po, 'reason', 'matchReason', 'match_reason', 'message', 'detail') ?? '');
  const reviewerNote = str(pick(pkg, 'reviewerNote', 'reviewer_note') ?? '');
  const hasOpenAmount = typeof openAmount === 'number' || (typeof openAmount === 'string' && openAmount.trim() !== '' && Number.isFinite(Number(openAmount)));

  return (
    <div className="pkg">
      {pkg == null && packageText.trim() !== '' && <p className="pkg-muted">The package is plain text, not JSON. Open the raw view below.</p>}

      <section>
        <h4>Agent narrative</h4>
        {narrative ? <p className="pkg-narrative">{narrative}</p> : <p className="pkg-muted">No narrative in this package.</p>}
        {riskFlags.length > 0 && (
          <ul className="pkg-flags" aria-label="Risk flags">
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
          <dt>PO matched</dt>
          <dd>{invoice.poMatched == null ? '—' : invoice.poMatched ? 'Yes' : 'No'}</dd>
          <dt>Open amount</dt>
          <dd className="mono">{hasOpenAmount ? formatMoney(Number(openAmount), invoice.currency) : '—'}</dd>
          <dt>Reason</dt>
          <dd>{poReason || '—'}</dd>
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
    return asObject(JSON.parse(text)) ?? null;
  } catch {
    return null;
  }
}

function asObject(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : undefined;
}

function pick(obj: unknown, ...keys: string[]): unknown {
  const o = asObject(obj);
  if (!o) return undefined;
  for (const k of keys) if (o[k] != null) return o[k];
  return undefined;
}

function narrativeText(pkg: Record<string, unknown> | null): string {
  const n = pick(pkg, 'narrative', 'summary', 'agentNarrative', 'agent_narrative');
  if (typeof n === 'string') return n;
  return str(pick(n, 'summary', 'text', 'narrative') ?? '');
}

function narrativeFlags(pkg: Record<string, unknown> | null): string[] {
  const flags = pick(pick(pkg, 'narrative'), 'risk_flags', 'riskFlags') ?? pick(pkg, 'riskFlags', 'risk_flags');
  return Array.isArray(flags) ? flags.map((f) => str(f)).filter(Boolean) : [];
}

function missingFields(recordValue: string, pkg: Record<string, unknown> | null): Set<string> {
  const fromPkg = pick(pick(pkg, 'decision'), 'missingApprovalFields') ?? pick(pkg, 'missingApprovalFields', 'missing_approval_fields');
  const list = Array.isArray(fromPkg) ? fromPkg.map((f) => str(f)) : [];
  recordValue
    .split(/[,;|\s]+/)
    .map((s) => s.replace(/[[\]"']/g, '').trim())
    .filter(Boolean)
    .forEach((s) => list.push(s));
  return new Set(list.map((s) => s.toLowerCase()));
}

const lowerFirst = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);
