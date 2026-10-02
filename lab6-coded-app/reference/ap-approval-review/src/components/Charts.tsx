/* Tiny inline SVG charts for the KPI cards and column coverage rings. No chart library. */

export function Sparkline({ values, width = 72, height = 28 }: { values: number[]; width?: number; height?: number }) {
  const max = Math.max(1, ...values);
  const stepX = values.length > 1 ? width / (values.length - 1) : width;
  const points = values.map((v, i) => [i * stepX, height - 2 - (v / max) * (height - 4)] as const);
  const path = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${path} L${width},${height} L0,${height} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Last 7 days: ${values.join(', ')}`}>
      <path d={area} fill="currentColor" opacity={0.12} />
      <path d={path} fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />
      {points.length > 0 && <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r={2.4} fill="currentColor" />}
    </svg>
  );
}

export function Donut({ value, total, size = 32, stroke = 5, label }: { value: number; total: number; size?: number; stroke?: number; label: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const ratio = total > 0 ? Math.min(1, value / total) : 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={stroke} opacity={0.15} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeDasharray={`${(ratio * c).toFixed(2)} ${c.toFixed(2)}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  );
}

export function CoverageRing({ percent }: { percent: number }) {
  return <Donut value={percent} total={100} size={14} stroke={3} label={`${percent}% of rows have a value`} />;
}
