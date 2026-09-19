import React from 'react';

// Small shared primitives in the control center's existing visual language.

export const panelStyle = {
  background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
  border: '1px solid rgba(139, 92, 246, 0.2)',
  borderRadius: '16px',
  padding: '20px',
  backdropFilter: 'blur(16px)',
  display: 'flex',
  flexDirection: 'column',
  gap: '14px',
};

export function Panel({ title, icon, right, children, style }) {
  return (
    <div style={{ ...panelStyle, ...style }}>
      {(title || right) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {icon}
            {title}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function PageHeader({ icon, title, subtitle, right }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          {icon}
          {title}
        </h1>
        {subtitle && <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Stat({ label, value, sub, color = '#fff' }) {
  return (
    <div style={{ background: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(139, 92, 246, 0.15)', borderRadius: '10px', padding: '12px' }}>
      <div style={{ fontSize: '0.66rem', color: 'rgba(196, 181, 253, 0.75)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      <div style={{ fontSize: '1.25rem', fontWeight: 800, color, marginTop: '3px' }}>{value}</div>
      {sub && <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.6)', marginTop: '2px' }}>{sub}</div>}
    </div>
  );
}

export function StatGrid({ children, min = 160 }) {
  return <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`, gap: '12px' }}>{children}</div>;
}

export function DataTable({ columns, rows, emptyText = 'No data yet.' }) {
  if (!rows || rows.length === 0) {
    return <div style={{ color: 'rgba(196, 181, 253, 0.7)', fontSize: '0.8rem' }}>{emptyText}</div>;
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: '#a78bfa', fontSize: '0.7rem', textTransform: 'uppercase' }}>
            {columns.map((c) => (
              <th key={c.key} style={{ padding: '8px 10px', borderBottom: '1px solid rgba(139, 92, 246, 0.2)' }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id ?? i} style={{ borderBottom: '1px solid rgba(139, 92, 246, 0.08)', color: '#e2e8f0' }}>
              {columns.map((c) => (
                <td key={c.key} style={{ padding: '9px 10px' }}>{c.render ? c.render(row) : row[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Note({ children, tone = 'info' }) {
  const tones = {
    info: ['rgba(82, 39, 255, 0.1)', 'rgba(139, 92, 246, 0.25)'],
    warn: ['rgba(245, 158, 11, 0.1)', 'rgba(245, 158, 11, 0.4)'],
    error: ['rgba(239, 68, 68, 0.1)', 'rgba(239, 68, 68, 0.45)'],
    ok: ['rgba(16, 185, 129, 0.1)', 'rgba(16, 185, 129, 0.4)'],
  };
  const [bg, border] = tones[tone];
  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: '8px', padding: '10px 14px', fontSize: '0.78rem', lineHeight: 1.5, color: 'rgba(226, 232, 240, 0.92)' }}>
      {children}
    </div>
  );
}

export function Btn({ onClick, disabled, children, tone = 'primary', title }) {
  const bg =
    tone === 'primary'
      ? 'linear-gradient(135deg, #5227FF 0%, #A855F7 100%)'
      : tone === 'ok'
      ? 'rgba(16, 185, 129, 0.25)'
      : 'rgba(255, 255, 255, 0.06)';
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        background: disabled ? 'rgba(82, 39, 255, 0.2)' : bg,
        border: tone === 'ok' ? '1px solid #10b981' : '1px solid rgba(168, 85, 247, 0.35)',
        color: '#fff',
        borderRadius: '8px',
        padding: '9px 16px',
        fontSize: '0.8rem',
        fontWeight: 700,
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {children}
    </button>
  );
}

export const fmt = {
  n: (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—' : Number(v).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d })),
  int: (v) => (v === null || v === undefined ? '—' : Math.round(v).toLocaleString()),
  pct: (a, b) => (b ? `${(((a - b) / b) * 100).toFixed(1)}%` : '—'),
};
