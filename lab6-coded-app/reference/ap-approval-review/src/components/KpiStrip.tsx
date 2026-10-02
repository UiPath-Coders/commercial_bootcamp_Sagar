import type { ReactNode } from 'react';
import { Donut, Sparkline } from './Charts';
import type { Kpis, KpiValue } from '@/data/useInvoices';

/**
 * Four compact metric cards. Definitions (docs/commercial-process.md):
 *  Total Invoices            = loaded rows (sparkline: new invoices per day, last 7 days)
 *  Approval Needed           = ApprovalNeeded = true
 *  Pending Review            = InvoiceLifecycleState in {NEEDS_AP_REVIEW, READY_FOR_APPROVAL}
 *  Recommended for Approval  = AgentRecommendation = READY_FOR_APPROVAL
 * A card whose backing field is absent from the live schema renders an explicit
 * empty state (dashed outline, muted value, caption naming the field) instead of 0.
 */
export function KpiStrip({ kpis, loading, missingField }: { kpis: Kpis; loading: boolean; missingField: (field: string) => boolean }) {
  return (
    <section className="kpi-grid" aria-label="Key metrics">
      <KpiCard
        label="Total Invoices"
        kpi={kpis.totalInvoices}
        loading={loading}
        missing={false}
        caption="New invoices per day, last 7 days"
        chart={<Sparkline values={kpis.totalInvoices.last7Days} />}
      />
      <KpiCard
        label="Approval Needed"
        kpi={kpis.approvalNeeded}
        loading={loading}
        missing={missingField(kpis.approvalNeeded.field)}
        caption="ApprovalNeeded = true"
      />
      <KpiCard
        label="Pending Review"
        kpi={kpis.pendingReview}
        loading={loading}
        missing={missingField(kpis.pendingReview.field)}
        caption="NEEDS_AP_REVIEW + READY_FOR_APPROVAL"
      />
      <KpiCard
        label="Recommended for Approval"
        kpi={kpis.recommendedForApproval}
        loading={loading}
        missing={missingField(kpis.recommendedForApproval.field)}
        caption="AgentRecommendation = READY_FOR_APPROVAL"
      />
    </section>
  );
}

function KpiCard({
  label,
  kpi,
  loading,
  missing,
  caption,
  chart,
}: {
  label: string;
  kpi: KpiValue;
  loading: boolean;
  missing: boolean;
  caption: string;
  chart?: ReactNode;
}) {
  const empty = missing || kpi.value == null;
  return (
    <article className="kpi" aria-busy={loading}>
      <span className="kpi-label">{label}</span>
      {loading ? (
        <>
          <span className="skeleton" style={{ width: 64, height: 30 }} aria-hidden />
          <span className="skeleton" style={{ width: 56, height: 28 }} aria-hidden />
          <span className="skeleton kpi-caption" style={{ width: '70%', height: 12 }} aria-hidden />
        </>
      ) : empty ? (
        <>
          <span className="kpi-value is-muted" aria-label="No value">
            —
          </span>
          <span className="kpi-empty-chart" aria-hidden />
          <span className="kpi-caption">
            Field <code>{kpi.field}</code> is not in the live schema
          </span>
        </>
      ) : (
        <>
          <span className="kpi-value">{kpi.value}</span>
          <span className="kpi-chart">
            {chart ?? <Donut value={kpi.value ?? 0} total={kpi.total} label={`${kpi.value} of ${kpi.total}`} />}
          </span>
          <span className="kpi-caption">{caption}</span>
        </>
      )}
    </article>
  );
}
