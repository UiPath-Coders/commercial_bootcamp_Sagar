import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, LoaderCircle, LockKeyhole, RefreshCw, Settings2, ShieldAlert } from 'lucide-react';
import type { AppError } from '@/data/errors';

/* Full-page status cards (auth / config) and in-table states (loading / empty / error). */

export function FullPageStatus({
  tone = 'blue',
  icon,
  title,
  children,
  actions,
}: {
  tone?: 'blue' | 'error' | 'warn' | 'teal';
  icon: ReactNode;
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  const toneClass = tone === 'error' ? 'is-error' : tone === 'warn' ? 'is-warn' : tone === 'teal' ? 'is-teal' : '';
  return (
    <div className="page-center">
      <section className="status-card" role="status" aria-live="polite">
        <div className={`status-icon ${toneClass}`}>{icon}</div>
        <h1>{title}</h1>
        {children}
        {actions && <div className="decision-row" style={{ justifyContent: 'center' }}>{actions}</div>}
      </section>
    </div>
  );
}

export function LoadingPage({ label }: { label: string }) {
  return (
    <FullPageStatus icon={<LoaderCircle size={22} className="spin" aria-hidden />} title={label}>
      <p>Talking to UiPath Automation Cloud.</p>
    </FullPageStatus>
  );
}

export function SignInPage({ onLogin, error }: { onLogin: () => void; error: string | null }) {
  return (
    <FullPageStatus icon={<LockKeyhole size={22} aria-hidden />} title="AP Approval Review" actions={<button className="btn btn-blue" onClick={onLogin}>Sign in with UiPath</button>}>
      <p>Sign in with your UiPath account to open the accounts-payable reviewer worklist.</p>
      {error && (
        <div className="banner is-error" role="alert">
          <ShieldAlert size={16} aria-hidden />
          <div className="banner-body">
            <strong>Sign-in failed.</strong> {error}
          </div>
        </div>
      )}
    </FullPageStatus>
  );
}

export function ConfigMissingPage() {
  return (
    <FullPageStatus tone="warn" icon={<Settings2 size={22} aria-hidden />} title="Entity id not configured">
      <p>
        This build still has the placeholder entity id. Set <code>invoiceEntityId</code> in <code>src/config/uipath.ts</code> to the GUID of your
        tenant-scoped <code>AP_Invoice_&lt;user_name&gt;</code> entity, then rebuild.
      </p>
      <code className="status-code">uip df entities list --output json</code>
    </FullPageStatus>
  );
}

export function ErrorBanner({ error, onRetry, onSignIn, compact }: { error: AppError; onRetry?: () => void; onSignIn?: () => void; compact?: boolean }) {
  const title =
    error.kind === 'auth'
      ? 'Authentication error'
      : error.kind === 'forbidden'
        ? 'Access denied'
        : error.kind === 'not-found'
          ? 'Entity not found'
          : 'Service error';
  return (
    <div className="banner is-error" role="alert">
      <ShieldAlert size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
      <div className="banner-body">
        <strong>{title}{error.status ? ` (${error.status})` : ''}.</strong> {error.message}
        {!compact && (
          <div className="decision-row" style={{ marginTop: 8 }}>
            {error.kind === 'auth' && onSignIn && (
              <button className="btn btn-secondary" onClick={onSignIn}>
                Sign in again
              </button>
            )}
            {onRetry && (
              <button className="btn btn-secondary" onClick={onRetry}>
                <RefreshCw size={14} aria-hidden /> Retry
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
    <div className="table-state" aria-busy="true">
      <LoaderCircle size={22} className="spin" aria-hidden />
      <h3>Loading invoices</h3>
      <p>Following the entity cursor until every record is loaded.</p>
    </div>
  );
}

export function TableEmpty({ hasSearch, onClear }: { hasSearch: boolean; onClear: () => void }) {
  return (
    <div className="table-state">
      <Inbox size={22} aria-hidden />
      <h3>{hasSearch ? 'No invoices match your search' : 'No invoices yet'}</h3>
      <p>
        {hasSearch
          ? 'Try a different vendor name or invoice number.'
          : 'The entity has no records. Run Lab 2 (intake) and Lab 5 (approval agent) to populate AP_Invoice_<user_name>.'}
      </p>
      {hasSearch && (
        <button className="btn btn-secondary" onClick={onClear}>
          Clear search
        </button>
      )}
    </div>
  );
}

export function TableError({ error, onRetry, onSignIn }: { error: AppError; onRetry: () => void; onSignIn: () => void }) {
  return (
    <div className="table-state" role="alert">
      <AlertTriangle size={22} aria-hidden style={{ color: 'var(--red-600)' }} />
      <h3>{error.kind === 'auth' ? 'Your session needs a refresh' : 'Could not load invoices'}</h3>
      <p>{error.message}</p>
      <div className="decision-row" style={{ justifyContent: 'center' }}>
        {error.kind === 'auth' && (
          <button className="btn btn-primary" onClick={onSignIn}>
            Sign in again
          </button>
        )}
        <button className="btn btn-secondary" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden /> Retry
        </button>
      </div>
    </div>
  );
}
