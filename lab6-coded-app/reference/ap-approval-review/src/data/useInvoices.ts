import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import type { EntityRecord } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/auth/AuthProvider';
import { UIPATH_CONFIG, folderScope, isEntityIdConfigured } from '@/config/uipath';
import { F, PENDING_REVIEW_STATES, RECOMMENDED_FOR_APPROVAL, TABLE_COLUMNS, type FieldName } from './invoiceFields';
import { isEmptyValue, toInvoice, type Invoice } from './invoiceModel';
import { toAppError, type AppError } from './errors';

/**
 * Loads AP_Invoice_<user_name> through the authenticated SDK.
 *
 * Data strategy (deliberate, see README "Design notes"):
 *  - ONE read path. `queryRecordsById` is followed cursor-by-cursor until
 *    `hasNextPage` is false (every SDK list call returns one page; there is no
 *    "give me everything" call). Each opaque `nextCursor` is passed back
 *    verbatim - never incremented.
 *  - KPIs, coverage, search, sort and table pagination are then derived from
 *    the loaded rows, so the four KPI cards are "derived from loaded data, not
 *    separate calls" and stay consistent with the table.
 *  - A participant entity holds tens of rows; the loop is capped at
 *    fetchPageSize * maxFetchPages rows and reports when the cap is hit.
 *    Beyond that scale, move search to a server-side `filterGroup` and KPIs to
 *    `aggregates` + `totalCount`.
 */

export type SortKey = (typeof TABLE_COLUMNS)[number]['key'];
export interface SortState {
  key: SortKey;
  direction: 'asc' | 'desc';
}

export interface KpiValue {
  /** Numeric value, or null when the backing field is absent from the schema (rendered as an empty state). */
  value: number | null;
  /** Denominator for the donut (total rows). */
  total: number;
  /** Field the card depends on. */
  field: FieldName;
}

export interface Kpis {
  totalInvoices: KpiValue & { /** New invoices per day for the last 7 days, oldest first. */ last7Days: number[] };
  approvalNeeded: KpiValue;
  pendingReview: KpiValue;
  recommendedForApproval: KpiValue;
}

export interface InvoicesState {
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: AppError | null;
  /** Every loaded row (unfiltered). */
  all: Invoice[];
  /** Rows after search + sort. */
  filtered: Invoice[];
  /** Current table page of `filtered`. */
  page: Invoice[];
  pageIndex: number;
  pageCount: number;
  setPageIndex: (i: number) => void;
  search: string;
  setSearch: (s: string) => void;
  sort: SortState;
  toggleSort: (key: SortKey) => void;
  /** % of loaded rows (0-100) where the field is non-empty, keyed by field name. */
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

function computeCoverage(rows: Invoice[]): Record<string, number> {
  const out: Record<string, number> = {};
  if (rows.length === 0) return out;
  const fields = new Set<string>();
  rows.forEach((r) => Object.keys(r.raw).forEach((k) => fields.add(k)));
  fields.forEach((f) => {
    const filled = rows.filter((r) => !isEmptyValue(r.raw[f])).length;
    out[f] = Math.round((filled / rows.length) * 100);
  });
  return out;
}

function computeKpis(rows: Invoice[], has: (f: FieldName) => boolean): Kpis {
  const total = rows.length;

  // Sparkline: invoices whose domain timestamp (ProcessedTimestamp, falling
  // back to the CreateTime audit column) falls in each of the last 7 UTC days.
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

export function useInvoices(hasField: (f: FieldName) => boolean): InvoicesState {
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
    if (!isAuthenticated || !isEntityIdConfigured() || inFlight.current) return;
    inFlight.current = true;
    setStatus('loading');
    setError(null);
    try {
      const entities = new Entities(sdk);
      const rows: EntityRecord[] = [];
      let pages = 0;
      let page = await entities.queryRecordsById(UIPATH_CONFIG.invoiceEntityId, {
        ...folderScope,
        pageSize: UIPATH_CONFIG.fetchPageSize,
        sortOptions: [{ fieldName: F.UpdateTime, isDescending: true }],
      });
      rows.push(...page.items);
      pages += 1;
      // Follow the opaque cursor; never treat it as a page number.
      while (page.hasNextPage && page.nextCursor && pages < UIPATH_CONFIG.maxFetchPages) {
        page = await entities.queryRecordsById(UIPATH_CONFIG.invoiceEntityId, {
          ...folderScope,
          pageSize: UIPATH_CONFIG.fetchPageSize,
          cursor: page.nextCursor,
        });
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
    const rows = q
      ? all.filter((r) => r.vendorName.toLowerCase().includes(q) || r.invoiceNumber.toLowerCase().includes(q))
      : all.slice();
    return rows.sort((a, b) => compare(a, b, sort));
  }, [all, search, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / UIPATH_CONFIG.pageSize));
  const safePage = Math.min(pageIndex, pageCount - 1);
  const page = useMemo(
    () => filtered.slice(safePage * UIPATH_CONFIG.pageSize, (safePage + 1) * UIPATH_CONFIG.pageSize),
    [filtered, safePage]
  );

  const coverage = useMemo(() => computeCoverage(all), [all]);
  const kpis = useMemo(() => computeKpis(filtered, hasField), [filtered, hasField]);

  const setSearch = (s: string) => {
    setSearchRaw(s);
    setPageIndexRaw(0);
  };
  const setPageIndex = (i: number) => setPageIndexRaw(Math.max(0, Math.min(i, pageCount - 1)));
  const toggleSort = (key: SortKey) =>
    setSort((prev) => (prev.key === key ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: key === 'updated' ? 'desc' : 'asc' }));
  const replaceInvoice = (next: Invoice) => setAll((prev) => prev.map((r) => (r.id === next.id ? next : r)));

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
