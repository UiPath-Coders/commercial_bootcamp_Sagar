import { AlertTriangle, Inbox, LoaderCircle, RefreshCw, ShieldAlert } from 'lucide-react';
import type { AppError } from '@/data/errors';

/* In-table states (loading / empty / error) and the inline error banner. */

function errorTitle(error: AppError): string {
  switch (error.kind) {
    case 'auth':
      return 'Authentication error';
    case 'forbidden':
      return 'Access denied';
    case 'not-found':
      return 'Entity not found';
    default:
      return 'Service error';
  }
}

export function ErrorBanner({ error, onRetry, onSignIn, retryLabel = 'Retry' }: { error: AppError; onRetry?: () => void; onSignIn?: () => void; retryLabel?: string }) {
  return (
    <div className="banner is-error" role="alert">
      <ShieldAlert size={16} aria-hidden className="banner-icon" />
      <div className="banner-body">
        <strong>
          {errorTitle(error)}
          {error.status ? ` (${error.status})` : ''}.
        </strong>{' '}
        {error.message}
        {(onRetry || (error.kind === 'auth' && onSignIn)) && (
          <div className="decision-row" style={{ marginTop: 8 }}>
            {error.kind === 'auth' && onSignIn && (
              <button type="button" className="btn btn-secondary" onClick={onSignIn}>
                Sign in again
              </button>
            )}
            {onRetry && (
              <button type="button" className="btn btn-secondary" onClick={onRetry}>
                <RefreshCw size={14} aria-hidden /> {retryLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function TableLoading() {
  return (
    <div className="table-state" aria-busy="true" role="status">
      <LoaderCircle size={22} className="spin" aria-hidden />
      <h3>Loading invoices</h3>
      <p>Reading every record from the entity.</p>
    </div>
  );
}

export function TableEmpty({ hasSearch, onClear, entityName }: { hasSearch: boolean; onClear: () => void; entityName: string }) {
  return (
    <div className="table-state">
      <Inbox size={22} aria-hidden />
      <h3>{hasSearch ? 'No invoices match your search' : 'No invoices yet'}</h3>
      <p>{hasSearch ? 'Try a different vendor name or invoice number.' : `${entityName} has no records yet. Run invoice intake and the approval agent to populate it.`}</p>
      {hasSearch && (
        <button type="button" className="btn btn-secondary" onClick={onClear}>
          Clear search
        </button>
      )}
    </div>
  );
}

export function TableError({ error, onRetry, onSignIn }: { error: AppError; onRetry: () => void; onSignIn: () => void }) {
  return (
    <div className="table-state" role="alert">
      <AlertTriangle size={22} aria-hidden className="text-danger" />
      <h3>{error.kind === 'auth' ? 'Your session needs a refresh' : 'Could not load invoices'}</h3>
      <p>
        <strong>
          {errorTitle(error)}
          {error.status ? ` (${error.status})` : ''}.
        </strong>{' '}
        {error.message}
      </p>
      <div className="decision-row" style={{ justifyContent: 'center' }}>
        {error.kind === 'auth' && (
          <button type="button" className="btn btn-primary" onClick={onSignIn}>
            Sign in again
          </button>
        )}
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden /> Retry
        </button>
      </div>
    </div>
  );
}
