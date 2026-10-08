import { useCallback, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/hooks/useAuth';
import { APP_CONFIG } from '@/config/app';
import { F, LIFECYCLE } from './fields';
import { isSizeMarker, mergeInvoice, toInvoice, type DecisionKind, type Invoice } from './invoice';
import { toAppError, type AppError } from './errors';

/**
 * The human decision, written to the SAME record through
 * entities.updateRecord({ name }, id, patch) (scope DataFabric.Data.Write):
 *   Approve : InvoiceLifecycleState = APPROVED
 *   Reject  : InvoiceLifecycleState = REJECTED, reason appended to ApprovalPackageJson as "reviewerNote"
 *   Both    : ReviewedBy = signed-in email, ReviewedAt = now (ISO)
 */

export interface DecisionResult {
  invoice: Invoice;
  /** Set when the reject reason could not be appended to the package. */
  warning: string | null;
}

export interface DecisionState {
  saving: DecisionKind | null;
  error: AppError | null;
  clearError: () => void;
  decide: (inv: Invoice, kind: DecisionKind, reason?: string) => Promise<DecisionResult | null>;
  /** Re-read one record (getRecordByName returns full text-field content). */
  fetchFull: (recordId: string) => Promise<Invoice>;
}

function appendReviewerNote(packageJson: string, note: string): { value: string | null; warning: string | null } {
  const trimmed = packageJson.trim();
  if (isSizeMarker(trimmed)) {
    // Writing the list-read marker back would destroy the real content.
    return { value: null, warning: 'ApprovalPackageJson could not be read in full, so the reason was not added to it. The decision itself was saved.' };
  }
  if (trimmed === '') return { value: JSON.stringify({ reviewerNote: note }, null, 2), warning: null };
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return { value: JSON.stringify({ ...(parsed as Record<string, unknown>), reviewerNote: note }, null, 2), warning: null };
    }
    return { value: JSON.stringify({ package: parsed, reviewerNote: note }, null, 2), warning: null };
  } catch {
    return { value: null, warning: 'ApprovalPackageJson is not valid JSON, so the reason was not added to it. The decision itself was saved.' };
  }
}

export function useDecision(): DecisionState {
  const { sdk, user } = useAuth();
  const [saving, setSaving] = useState<DecisionKind | null>(null);
  const [error, setError] = useState<AppError | null>(null);

  const fetchFull = useCallback(
    async (recordId: string) => toInvoice(await new Entities(sdk).getRecordByName(APP_CONFIG.invoiceEntityName, recordId)),
    [sdk]
  );

  const decide = useCallback(
    async (inv: Invoice, kind: DecisionKind, reason?: string): Promise<DecisionResult | null> => {
      if (!user?.email) {
        setError({ kind: 'auth', message: 'Your signed-in email is unknown, so ReviewedBy cannot be written. Sign out and sign in again.' });
        return null;
      }
      setSaving(kind);
      setError(null);
      try {
        const patch: Record<string, unknown> = {
          [F.InvoiceLifecycleState]: kind === 'approve' ? LIFECYCLE.APPROVED : LIFECYCLE.REJECTED,
          [F.ReviewedBy]: user.email,
          [F.ReviewedAt]: new Date().toISOString(),
        };

        let warning: string | null = null;
        if (kind === 'reject') {
          // Append to the freshest full package, not a possibly stale or truncated copy.
          let fullPackage = inv.approvalPackageJson;
          try {
            fullPackage = (await fetchFull(inv.id)).approvalPackageJson;
          } catch {
            /* keep the loaded copy; appendReviewerNote guards against a size marker */
          }
          const note = appendReviewerNote(fullPackage, (reason ?? '').trim());
          if (note.value != null) patch[F.ApprovalPackageJson] = note.value;
          warning = note.warning;
        }

        const response = await new Entities(sdk).updateRecord({ name: APP_CONFIG.invoiceEntityName }, inv.id, patch);
        // Merge the patch under the response so the row reflects the write even on a partial body.
        const next = mergeInvoice(inv, { ...patch, ...(response as Record<string, unknown>) });
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

  return { saving, error, clearError: useCallback(() => setError(null), []), decide, fetchFull };
}
