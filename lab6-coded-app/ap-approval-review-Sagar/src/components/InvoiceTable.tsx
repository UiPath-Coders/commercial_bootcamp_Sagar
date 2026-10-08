import { useState } from 'react';
import type { MouseEvent } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Check, ChevronLeft, ChevronRight, Copy } from 'lucide-react';
import { CoverageRing } from './Charts';
import { EvaluationTag } from './EvaluationTag';
import { TABLE_COLUMNS } from '@/data/fields';
import { approvalPill, formatDateTime, formatMoney, initials, type Invoice } from '@/data/invoice';
import type { InvoicesState } from '@/data/useInvoices';
import { APP_CONFIG } from '@/config/app';

export function InvoiceTable({
  invoices,
  selectedId,
  onSelect,
  missingField,
}: {
  invoices: InvoicesState;
  selectedId: string | null;
  onSelect: (inv: Invoice) => void;
  missingField: (field: string) => boolean;
}) {
  const { page, sort, toggleSort, coverage } = invoices;

  return (
    <>
      <div className="table-scroll">
        <table className="invoices">
          <thead>
            <tr>
              {TABLE_COLUMNS.map((col) => {
                const isMissing = missingField(col.field);
                const pct = isMissing ? 0 : (coverage[col.field] ?? 0);
                const active = sort.key === col.key;
                return (
                  <th key={col.key} scope="col" aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <span className="th-inner">
                      {col.sortable ? (
                        <button type="button" className="th-sort" onClick={() => toggleSort(col.key)} title={`Sort by ${col.label}`}>
                          {col.label}
                          {active ? (
                            sort.direction === 'asc' ? (
                              <ArrowUp size={12} aria-hidden />
                            ) : (
                              <ArrowDown size={12} aria-hidden />
                            )
                          ) : (
                            <ArrowUpDown size={12} aria-hidden style={{ opacity: 0.5 }} />
                          )}
                        </button>
                      ) : (
                        col.label
                      )}
                      <span
                        className={`coverage ${isMissing ? 'is-missing' : ''}`}
                        title={isMissing ? `${col.field} is not in the live schema` : `${pct}% of loaded rows have ${col.field}`}
                      >
                        <CoverageRing percent={pct} />
                        {isMissing ? 'n/a' : `${pct}%`}
                      </span>
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {page.map((inv) => (
              <InvoiceRow key={inv.id} inv={inv} selected={inv.id === selectedId} onSelect={() => onSelect(inv)} />
            ))}
          </tbody>
        </table>
      </div>
      <Pagination invoices={invoices} />
    </>
  );
}

function InvoiceRow({ inv, selected, onSelect }: { inv: Invoice; selected: boolean; onSelect: () => void }) {
  const [copied, setCopied] = useState(false);
  const copyId = async (e: MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(inv.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable; the id is still shown in the detail panel */
    }
  };
  const updated = inv.updateTime ?? inv.agentProcessedAt ?? inv.processedTimestamp;
  const pill = approvalPill(inv);

  return (
    <tr
      className={selected ? 'is-selected' : ''}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      tabIndex={0}
      aria-selected={selected}
      aria-label={`Open invoice ${inv.invoiceNumber || 'without number'} from ${inv.vendorName || 'unknown vendor'}`}
    >
      <td>
        <div className="vendor-cell">
          <span className="avatar" aria-hidden>
            {initials(inv.vendorName || inv.invoiceNumber)}
          </span>
          <span className="vendor-text">
            <span className="vendor-name" title={inv.vendorName}>
              {inv.vendorName || <span className="cell-dash">Unknown vendor</span>}
            </span>
            <span className="vendor-sub" title={inv.invoiceNumber}>
              {inv.invoiceNumber || '—'}
              <EvaluationTag invoiceNumber={inv.invoiceNumber} />
            </span>
          </span>
          <button
            type="button"
            className="btn-icon copy-id"
            onClick={copyId}
            onKeyDown={(e) => e.stopPropagation()}
            title={copied ? 'Copied' : 'Copy record ID'}
            aria-label={copied ? 'Record ID copied' : 'Copy record ID'}
          >
            {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
          </button>
        </div>
      </td>
      <td className="cell-mono">{inv.poNumber || <span className="cell-dash">—</span>}</td>
      <td className="cell-mono">{formatMoney(inv.totalAmount, inv.currency)}</td>
      <td>{pill ? <span className={pill.tone === 'needed' ? 'pill pill-amber' : 'pill pill-word'}>{pill.text}</span> : <span className="cell-dash">—</span>}</td>
      <td>{inv.lifecycleState ? <span className="pill">{inv.lifecycleState}</span> : <span className="cell-dash">—</span>}</td>
      <td className="cell-mono cell-muted">{inv.agentRecommendation || <span className="cell-dash">—</span>}</td>
      <td className="cell-mono cell-muted">{formatDateTime(updated)}</td>
    </tr>
  );
}

function Pagination({ invoices }: { invoices: InvoicesState }) {
  const { filtered, pageIndex, pageCount, setPageIndex } = invoices;
  const from = filtered.length === 0 ? 0 : pageIndex * APP_CONFIG.pageSize + 1;
  const to = Math.min(filtered.length, (pageIndex + 1) * APP_CONFIG.pageSize);
  return (
    <nav className="pagination" aria-label="Table pagination">
      <span>
        Showing <strong>{from}</strong>–<strong>{to}</strong> of <strong>{filtered.length}</strong>
      </span>
      <div className="pagination-controls">
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPageIndex(pageIndex - 1)} disabled={pageIndex === 0} title="Previous page">
          <ChevronLeft size={14} aria-hidden /> Previous
        </button>
        <span className="page-num">
          Page {pageIndex + 1} of {pageCount}
        </span>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPageIndex(pageIndex + 1)} disabled={pageIndex >= pageCount - 1} title="Next page">
          Next <ChevronRight size={14} aria-hidden />
        </button>
      </div>
    </nav>
  );
}
