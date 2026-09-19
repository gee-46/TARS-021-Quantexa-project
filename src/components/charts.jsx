import React from 'react';

// Dependency-free SVG charts. All values are passed in from real API results.

const W = 640;
const H = 260;
const PAD = { l: 56, r: 16, t: 14, b: 40 };

function scale(values, pad = 0.08) {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || Math.abs(hi) || 1;
  return [lo - span * pad, hi + span * pad];
}

const tick = (v) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : Number(v).toFixed(Math.abs(v) < 10 ? 1 : 0));

/**
 * series: [{ name, color, points: [{x, y, label?}], dashed? }]
 * highlight: optional {x, y} point to ring.
 */
export function LineChart({ series, xLabel, yLabel, highlight, height = H, yDomain, xDomain }) {
  const all = series.flatMap((s) => s.points);
  if (all.length === 0) return null;
  const [x0, x1] = xDomain || scale(all.map((p) => p.x), 0.04);
  const [y0, y1] = yDomain || scale(all.map((p) => p.y));
  const sx = (x) => PAD.l + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);
  const sy = (y) => H - PAD.b - ((y - y0) / (y1 - y0 || 1)) * (H - PAD.t - PAD.b);
  const ticks = [0, 1, 2, 3, 4];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height }} role="img" aria-label={`${yLabel} versus ${xLabel}`}>
        {ticks.map((i) => {
          const yv = y0 + ((y1 - y0) * i) / 4;
          const xv = x0 + ((x1 - x0) * i) / 4;
          return (
            <g key={i}>
              <line x1={PAD.l} x2={W - PAD.r} y1={sy(yv)} y2={sy(yv)} stroke="rgba(139,92,246,.14)" />
              <text x={PAD.l - 8} y={sy(yv) + 4} textAnchor="end" fontSize="10" fill="rgba(196,181,253,.75)">{tick(yv)}</text>
              <text x={sx(xv)} y={H - PAD.b + 16} textAnchor="middle" fontSize="10" fill="rgba(196,181,253,.75)">{tick(xv)}</text>
            </g>
          );
        })}
        <text x={(PAD.l + W - PAD.r) / 2} y={H - 6} textAnchor="middle" fontSize="11" fill="#c4b5fd">{xLabel}</text>
        <text x={12} y={(PAD.t + H - PAD.b) / 2} textAnchor="middle" fontSize="11" fill="#c4b5fd" transform={`rotate(-90 12 ${(PAD.t + H - PAD.b) / 2})`}>{yLabel}</text>
        {series.map((s) => (
          <g key={s.name}>
            <polyline
              fill="none"
              stroke={s.color}
              strokeWidth="2.2"
              strokeDasharray={s.dashed ? '5 4' : undefined}
              points={s.points.map((p) => `${sx(p.x)},${sy(p.y)}`).join(' ')}
            />
            {s.points.map((p, i) => (
              <g key={i}>
                <circle cx={sx(p.x)} cy={sy(p.y)} r="4" fill={s.color}>
                  <title>{`${s.name}: ${p.label ?? `${xLabel} ${p.x}, ${yLabel} ${p.y}`}`}</title>
                </circle>
              </g>
            ))}
          </g>
        ))}
        {highlight && <circle cx={sx(highlight.x)} cy={sy(highlight.y)} r="9" fill="none" stroke="#fff" strokeWidth="2" />}
      </svg>
      <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', fontSize: '0.72rem', color: 'rgba(226,232,240,.85)' }}>
        {series.map((s) => (
          <span key={s.name} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '14px', height: '3px', background: s.color, display: 'inline-block' }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Horizontal bars: items [{label, value, color}] (values may be negative). */
export function BarChart({ items, unit = '' }) {
  if (!items.length) return null;
  const min = Math.min(0, ...items.map((i) => i.value));
  const max = Math.max(0, ...items.map((i) => i.value));
  const span = max - min || 1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {items.map((i) => {
        const left = ((Math.min(0, i.value) - min) / span) * 100;
        const width = (Math.abs(i.value) / span) * 100;
        return (
          <div key={i.label} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 90px', alignItems: 'center', gap: '10px', fontSize: '0.75rem', color: '#e2e8f0' }}>
            <span style={{ fontWeight: 700 }}>{i.label}</span>
            <div style={{ position: 'relative', height: '16px', background: 'rgba(255,255,255,.05)', borderRadius: '4px' }}>
              <div style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, height: '100%', background: i.color, borderRadius: '4px' }} />
            </div>
            <span style={{ textAlign: 'right', fontFamily: 'monospace' }}>{i.value.toFixed(2)}{unit}</span>
          </div>
        );
      })}
    </div>
  );
}
