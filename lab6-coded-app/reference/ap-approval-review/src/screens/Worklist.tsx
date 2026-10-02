import { useCallback, useState } from 'react';
import { AlertTriangle, ClipboardCheck, Info, LogOut, RefreshCw, Search, X } from 'lucide-react';
import { useAuth } from '@/auth/AuthProvider';
import { useInvoiceSchema, fieldMissing } from '@/data/schema';
import { useInvoices } from '@/data/useInvoices';
import { useReviewDecision } from '@/data/useReviewDecision';
import type { Invoice } from '@/data/invoiceModel';
import type { FieldName } from '@/data/invoiceFields';
import { KpiStrip } from '@/components/KpiStrip';
import { InvoiceTable } from '@/components/InvoiceTable';
import { InvoiceDetailPanel } from '@/components/InvoiceDetailPanel';
import { ErrorBanner, TableEmpty, TableError, TableLoading } from '@/components/StateViews';

/** Screen 2 — the AP reviewer worklist (Review & Approve, the human-in-the-loop step). */
export function Worklist() {
  const { user, profileWarning, logout, login } = useAuth();
  const schema = useInvoiceSchema();
  const hasField = useCallback((f: FieldName) => !fieldMissing(schema, f), [schema]);
  const invoices = useInvoices(hasField);
  const decision = useReviewDecision();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = selectedId ? invoices.all.find((r) => r.id === selectedId) ?? null : null;
  const loading = invoices.status === 'loading' || invoices.status === 'idle';
  const missingField = (f: string) => fieldMissing(schema, f as FieldName);

  const reload = () => {
    schema.reload();
    invoices.reload();
  };

  const onUpdated = (next: Invoice) => invoices.replaceInvoice(next);

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            <ClipboardCheck size={16} />
          </span>
          <div style={{ minWidth: 0 }}>
            <h1>AP Approval Review</h1>
            <div className="brand-sub">{schema.entityName || 'AP_Invoice'} · customersuccessamer / Training</div>
          </div>
        </div>
        <div className="header-right">
          {user && (
            <span className="user-chip" title={user.email}>
              <span className="avatar" style={{ width: 24, height: 24, fontSize: 10 }} aria-hidden>
                {user.name.slice(0, 2).toUpperCase()}
              </span>
              <span className="email">{user.email}</span>
            </span>
          )}
          <button className="btn-icon" onClick={reload} title="Refresh" aria-label="Refresh invoices" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : undefined} aria-hidden />
          </button>
          <button className="btn-icon" onClick={logout} title="Sign out" aria-label="Sign out">
            <LogOut size={16} aria-hidden />
          </button>
        </div>
      </header>

      <main className="worklist">
        <KpiStrip kpis={invoices.kpis} loading={loading} missingField={missingField} />

        {/* Data-integrity banner: UI-dependent fields missing from the live schema (shown once). */}
        {schema.status === 'ready' && schema.missingUiFields.length > 0 && (
          <div className="banner" role="alert">
            <AlertTriangle size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
            <div className="banner-body">
              <strong>Partial data.</strong> The live schema of <code>{schema.entityName}</code> is missing{' '}
              {schema.missingUiFields.map((f, i) => (
                <span key={f}>
                  {i > 0 && ', '}
                  <code>{f}</code>
                </span>
              ))}
              . KPIs and decisions that depend on them are disabled. Add the Lab 5 fields (Lab 5 step 2) and refresh.
            </div>
          </div>
        )}
        {schema.status === 'error' && schema.error && (
          <div className="banner">
            <Info size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
            <div className="banner-body">
              <strong>Schema check unavailable.</strong> {schema.error.message} Field coverage is inferred from the loaded rows instead.{' '}
              <button className="btn-link" onClick={schema.reload}>
                Retry
              </button>
            </div>
          </div>
        )}
        {profileWarning && (
          <div className="banner">
            <Info size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
            <div className="banner-body">{profileWarning}</div>
          </div>
        )}
        {invoices.reachedCap && (
          <div className="banner is-info">
            <Info size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
            <div className="banner-body">
              Loaded the first {invoices.all.length} records; the entity has more. Raise <code>maxFetchPages</code> in <code>src/config/uipath.ts</code> or move search to a server-side filter.
            </div>
          </div>
        )}
        {invoices.status === 'error' && invoices.error && invoices.all.length > 0 && <ErrorBanner error={invoices.error} onRetry={invoices.reload} onSignIn={login} />}

        <div className="toolbar">
          <div className="search">
            <Search size={15} className="search-icon" aria-hidden />
            <input
              type="search"
              value={invoices.search}
              onChange={(e) => invoices.setSearch(e.target.value)}
              placeholder="Search vendor name or invoice number"
              aria-label="Search by vendor name or invoice number"
              disabled={loading && invoices.all.length === 0}
            />
            {invoices.search && (
              <button className="btn-icon search-clear" onClick={() => invoices.setSearch('')} title="Clear search" aria-label="Clear search">
                <X size={14} aria-hidden />
              </button>
            )}
          </div>
          <div className="toolbar-right">
            {invoices.refreshedAt && <span>Refreshed {invoices.refreshedAt.toLocaleTimeString()}</span>}
          </div>
        </div>

        <section className="table-card" aria-label="Invoice worklist">
          {invoices.status === 'error' && invoices.all.length === 0 && invoices.error ? (
            <TableError error={invoices.error} onRetry={invoices.reload} onSignIn={login} />
          ) : loading && invoices.all.length === 0 ? (
            <TableLoading />
          ) : invoices.filtered.length === 0 ? (
            <TableEmpty hasSearch={invoices.search.trim() !== ''} onClear={() => invoices.setSearch('')} />
          ) : (
            <InvoiceTable invoices={invoices} selectedId={selectedId} onSelect={(inv) => setSelectedId(inv.id)} missingField={missingField} />
          )}
        </section>
      </main>

      {selected && (
        <InvoiceDetailPanel
          invoice={selected}
          schema={schema}
          decision={decision}
          reviewerEmail={user?.email ?? null}
          onClose={() => setSelectedId(null)}
          onUpdated={onUpdated}
          onSignIn={login}
        />
      )}
    </>
  );
}
