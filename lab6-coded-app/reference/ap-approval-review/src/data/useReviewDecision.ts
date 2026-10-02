import { useCallback, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/auth/AuthProvider';
import { UIPATH_CONFIG, folderScope } from '@/config/uipath';
import { F, LIFECYCLE } from './invoiceFields';
import { isSizeMarker, mergeInvoice, toInvoice, type DecisionKind, type Invoice } from './invoiceModel';
import { toAppError, type AppError } from './errors';

/**
 * The human-in-the-loop write: the "Approved?" gateway of the process.
 *
 *   Approve : InvoiceLifecycleState = APPROVED
 *   Reject  : InvoiceLifecycleState = REJECTED, reason appended to
 *             ApprovalPackageJson under "reviewerNote"
 *   Both    : ReviewedBy = signed-in email, ReviewedAt = ISO now
 *
 * Written with `entities.updateRecordById` (scope: DataFabric.Data.Write) to
 * the SAME record the Lab 5 agent wrote. The response (which echoes the
 * record) is merged into the local row so the table and panel update without
 * a full reload.
 */

export interface DecisionResult {
  invoice: Invoice;
  /** Set when the reject reason could not be appended (package not JSON / size marker). */
  warning: string | null;
}

export interface DecisionState {
  saving: DecisionKind | null;
  error: AppError | null;
  clearError: () => void;
  approve: (inv: Invoice) => Promise<DecisionResult | null>;
  reject: (inv: Invoice, reason: string) => Promise<DecisionResult | null>;
  /** Re-read one record by id (returns full MULTILINE_MAX content, unlike list reads). */
  fetchFull: (recordId: string) => Promise<Invoice>;
}

function appendReviewerNote(packageJson: string, note: string): { value: string | null; warning: string | null } {
  const trimmed = packageJson.trim();
  if (isSizeMarker(trimmed)) {
    // Echoing the list-read marker back would destroy the real content.
    return { value: null, warning: 'ApprovalPackageJson could not be re-read in full, so the reason was not appended to it.' };
  }
  if (trimmed === '') {
    return { value: JSON.stringify({ reviewerNote: note }, null, 2), warning: null };
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return { value: JSON.stringify({ ...(parsed as Record<string, unknown>), reviewerNote: note }, null, 2), warning: null };
    }
    return { value: JSON.stringify({ package: parsed, reviewerNote: note }, null, 2), warning: null };
  } catch {
    return { value: null, warning: 'ApprovalPackageJson is not valid JSON, so the reason was not appended to it. The decision itself was saved.' };
  }
}

export function useReviewDecision(): DecisionState {
  const { sdk, user } = useAuth();
  const [saving, setSaving] = useState<DecisionKind | null>(null);
  const [error, setError] = useState<AppError | null>(null);

  const fetchFull = useCallback(
    async (recordId: string) => {
      const entities = new Entities(sdk);
      const record = await entities.getRecordById(UIPATH_CONFIG.invoiceEntityId, recordId, folderScope);
      return toInvoice(record);
    },
    [sdk]
  );

  const write = useCallback(
    async (inv: Invoice, kind: DecisionKind, reason?: string): Promise<DecisionResult | null> => {
      if (!user?.email) {
        setError({ kind: 'auth', message: 'Your signed-in email is unknown, so ReviewedBy cannot be written. Sign out and back in.' });
        return null;
      }
      setSaving(kind);
      setError(null);
      try {
        const entities = new Entities(sdk);
        const payload: Record<string, unknown> = {
          [F.InvoiceLifecycleState]: kind === 'approve' ? LIFECYCLE.APPROVED : LIFECYCLE.REJECTED,
          [F.ReviewedBy]: user.email,
          [F.ReviewedAt]: new Date().toISOString(),
        };

        let warning: string | null = null;
        if (kind === 'reject') {
          // Use the full record so the note lands on the real package, not a list-read marker.
          let fullPackage = inv.approvalPackageJson;
          if (isSizeMarker(fullPackage)) {
            try {
              fullPackage = (await fetchFull(inv.id)).approvalPackageJson;
            } catch {
              /* fall through: appendReviewerNote reports the marker */
            }
          }
          const note = appendReviewerNote(fullPackage, (reason ?? '').trim());
          if (note.value != null) payload[F.ApprovalPackageJson] = note.value;
          warning = note.warning;
        }

        const response = await entities.updateRecordById(UIPATH_CONFIG.invoiceEntityId, inv.id, payload, folderScope);
        // The response echoes the record; merge the payload underneath so the
        // local row reflects the write even if the server returns a partial body.
        const next = mergeInvoice(inv, { ...payload, ...(response as Record<string, unknown>) });
        return { invoice: next, warning };
      } catch (err) {
        setError(toAppError(err, `Unable to ${kind} this invoice.`));
        return null;
      } finally {
        setSaving(null);
      }
    },
    [sdk, user?.email, fetchFull]
  );

  return {
    saving,
    error,
    clearError: () => setError(null),
    approve: (inv) => write(inv, 'approve'),
    reject: (inv, reason) => write(inv, 'reject', reason),
    fetchFull,
  };
}
