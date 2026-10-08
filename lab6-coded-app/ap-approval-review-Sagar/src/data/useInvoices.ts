import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import type { EntityRecord } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/hooks/useAuth';
import { APP_CONFIG } from '@/config/app';
import { F, PENDING_REVIEW_STATES, RECOMMENDED_FOR_APPROVAL, type FieldName, type SortKey } from './fields';
import { isEmptyValue, toInvoice, type Invoice } from './invoice';
import { toAppError, type AppError } from './errors';

/**
 * Loads AP_Invoice_Sagar with entities.getRecordsByName, following the opaque
 * cursor until hasNextPage is false (every SDK list call returns ONE page).
 * KPIs, coverage, search, sort and table pagination are derived from the
 * loaded rows, so the KPI cards always agree with the table.
 */

export interface SortState {
  key: SortKey;
  direction: 'asc' | 'desc';
}

export interface KpiValue {
  /** null when the backing field is absent from the schema (rendered as an empty state). */
  value: number | null;
  total: number;
  field: FieldName;
}

export interface Kpis {
  totalInvoices: KpiValue & { /** Invoices per day for the last 7 days, oldest first. */ last7Days: number[] };
  approvalNeeded: KpiValue;
  pendingReview: KpiValue;
  recommendedForApproval: KpiValue;
}

export interface InvoicesState {
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: AppError | null;
  all: Invoice[];
  filtered: Invoice[];
  page: Invoice[];
  pageIndex: number;
  pageCount: number;
  setPageIndex: (i: number) => void;
  search: string;
  setSearch: (s: string) => void;
  sort: SortState;
  toggleSort: (key: SortKey) => void;
  /** % of loaded rows (0-100) where the field is non-null, keyed by field name. */
  coverage: Record<string, number>;
  kpis: Kpis;
  reachedCap: boolean;
  refreshedAt: Date | null;
  reload: () => void;
  /** Replace one row in place after a successful write (no full reload). */
  replaceInvoice: (next: Invoice) => void;
}

function compare(a: Invoice, b: Invoice, sort: SortState): number {
  const dir = sort.direction === 'asc' ? 1 : -1;
  const text = (x: string, y: string) => x.localeCompare(y, undefined, { sensitivity: 'base' }) * dir;
  const number = (x: number | null, y: number | null) => ((x ?? -Infinity) - (y ?? -Infinity)) * dir;
  const time = (x: Date | null, y: Date | null) => ((x?.getTime() ?? 0) - (y?.getTime() ?? 0)) * dir;
  switch (sort.key) {
    case 'vendor':
      return text(a.vendorName, b.vendorName) || text(a.invoiceNumber, b.invoiceNumber);
    case 'po':
      return text(a.poNumber, b.poNumber);
    case 'total':
      return number(a.totalAmount, b.totalAmount);
    case 'approvalNeeded':
      return number(a.approvalNeeded ? 1 : 0, b.approvalNeeded ? 1 : 0);
    case 'lifecycle':
      return text(a.lifecycleState, b.lifecycleState);
    case 'recommendation':
      return text(a.agentRecommendation, b.agentRecommendation);
    case 'updated':
    default:
      return time(a.updateTime ?? a.processedTimestamp, b.updateTime ?? b.processedTimestamp);
  }
}

/** Coverage over the schema fields when known, else over every key seen in the rows. */
function computeCoverage(rows: Invoice[], schemaFields: Set<string>): Record<string, number> {
  const out: Record<string, number> = {};
  if (rows.length === 0) return out;
  const fields = new Set<string>(schemaFields);
  rows.forEach((r) => Object.keys(r.raw).forEach((k) => fields.add(k)));
  fields.forEach((f) => {
    const filled = rows.filter((r) => !isEmptyValue(r.raw[f])).length;
    out[f] = Math.round((filled / rows.length) * 100);
  });
  return out;
}

function computeKpis(rows: Invoice[], has: (f: FieldName) => boolean): Kpis {
  const total = rows.length;

  // Sparkline: invoices whose ProcessedTimestamp (falling back to CreateTime)
  // falls in each of the last 7 UTC days, oldest first.
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);
  const buckets = new Array<number>(7).fill(0);
  rows.forEach((r) => {
    const d = r.processedTimestamp ?? r.createTime;
    if (!d) return;
    const dayDiff = Math.floor((today.getTime() - Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())) / 86_400_000);
    if (dayDiff >= 0 && dayDiff < 7) buckets[6 - dayDiff] += 1;
  });

  return {
    totalInvoices: { value: total, total, field: F.Id, last7Days: buckets },
    approvalNeeded: {
      value: has(F.ApprovalNeeded) ? rows.filter((r) => r.approvalNeeded === true).length : null,
      total,
      field: F.ApprovalNeeded,
    },
    pendingReview: {
      value: has(F.InvoiceLifecycleState) ? rows.filter((r) => PENDING_REVIEW_STATES.includes(r.lifecycleState)).length : null,
      total,
      field: F.InvoiceLifecycleState,
    },
    recommendedForApproval: {
      value: has(F.AgentRecommendation) ? rows.filter((r) => r.agentRecommendation === RECOMMENDED_FOR_APPROVAL).length : null,
      total,
      field: F.AgentRecommendation,
    },
  };
}

export function useInvoices(hasField: (f: FieldName) => boolean, schemaFields: Set<string>): InvoicesState {
  const { sdk, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<InvoicesState['status']>('idle');
  const [error, setError] = useState<AppError | null>(null);
  const [all, setAll] = useState<Invoice[]>([]);
  const [reachedCap, setReachedCap] = useState(false);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
  const [search, setSearchRaw] = useState('');
  const [sort, setSort] = useState<SortState>({ key: 'updated', direction: 'desc' });
  const [pageIndex, setPageIndexRaw] = useState(0);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (!isAuthenticated || inFlight.current) return;
    inFlight.current = true;
    setStatus('loading');
    setError(null);
    try {
      const entities = new Entities(sdk);
      const rows: EntityRecord[] = [];
      let pages = 1;
      let page = await entities.getRecordsByName(APP_CONFIG.invoiceEntityName, { pageSize: APP_CONFIG.fetchPageSize });
      rows.push(...page.items);
      // Pass each opaque cursor back verbatim; never treat it as a page number.
      while (page.hasNextPage && page.nextCursor && pages < APP_CONFIG.maxFetchPages) {
        page = await entities.getRecordsByName(APP_CONFIG.invoiceEntityName, { cursor: page.nextCursor });
        rows.push(...page.items);
        pages += 1;
      }
      setReachedCap(Boolean(page.hasNextPage && page.nextCursor));
      setAll(rows.map(toInvoice));
      setRefreshedAt(new Date());
      setStatus('ready');
    } catch (err) {
      setError(toAppError(err, 'Unable to load invoices.'));
      setStatus('error');
    } finally {
      inFlight.current = false;
    }
  }, [sdk, isAuthenticated]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = q ? all.filter((r) => r.vendorName.toLowerCase().includes(q) || r.invoiceNumber.toLowerCase().includes(q)) : all.slice();
    return rows.sort((a, b) => compare(a, b, sort));
  }, [all, search, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / APP_CONFIG.pageSize));
  const safePage = Math.min(pageIndex, pageCount - 1);
  const page = useMemo(() => filtered.slice(safePage * APP_CONFIG.pageSize, (safePage + 1) * APP_CONFIG.pageSize), [filtered, safePage]);

  const coverage = useMemo(() => computeCoverage(all, schemaFields), [all, schemaFields]);
  const kpis = useMemo(() => computeKpis(filtered, hasField), [filtered, hasField]);

  const setSearch = (s: string) => {
    setSearchRaw(s);
    setPageIndexRaw(0);
  };
  const setPageIndex = (i: number) => setPageIndexRaw(Math.max(0, Math.min(i, pageCount - 1)));
  const toggleSort = (key: SortKey) =>
    setSort((prev) => (prev.key === key ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: key === 'updated' ? 'desc' : 'asc' }));
  const replaceInvoice = useCallback((next: Invoice) => setAll((prev) => prev.map((r) => (r.id === next.id ? next : r))), []);

  return {
    status,
    error,
    all,
    filtered,
    page,
    pageIndex: safePage,
    pageCount,
    setPageIndex,
    search,
    setSearch,
    sort,
    toggleSort,
    coverage,
    kpis,
    reachedCap,
    refreshedAt,
    reload: load,
    replaceInvoice,
  };
}
