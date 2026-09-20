import React from 'react';

// Shared operational-panel primitives (light control-room theme; tokens live in index.css).

export const panelStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  padding: '14px 16px',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

export function Panel({ title, icon, right, children, style }) {
  return (
    <section style={{ ...panelStyle, ...style }}>
      {(title || right) && (
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border)', paddingBottom: '8px', margin: '-2px 0 0' }}>
          <h2 style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-2)', letterSpacing: '0.06em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {icon}
            {title}
          </h2>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({ icon, title, subtitle, right }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '12px', flexWrap: 'wrap' }}>
      <div>
        <h1 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          {icon}
          {title}
        </h1>
        {subtitle && <p style={{ fontSize: '0.82rem', color: 'var(--muted)', marginTop: '3px', maxWidth: '900px' }}>{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Stat({ label, value, sub, color = 'var(--text)' }) {
  return (
    <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '8px 10px' }}>
      <div style={{ fontSize: '0.66rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: '1.15rem', fontWeight: 700, color, marginTop: '2px', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: '0.68rem', color: 'var(--muted)', marginTop: '1px' }}>{sub}</div>}
    </div>
  );
}

export function StatGrid({ children, min = 150 }) {
  return <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`, gap: '10px' }}>{children}</div>;
}

export function DataTable({ columns, rows, emptyText = 'No data yet.' }) {
  if (!rows || rows.length === 0) {
    return <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>{emptyText}</div>;
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: 'var(--muted)', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {columns.map((c) => (
              <th key={c.key} style={{ padding: '6px 10px', borderBottom: '2px solid var(--border)', fontWeight: 700 }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id ?? i} style={{ borderBottom: '1px solid var(--surface-3)', color: 'var(--text)' }}>
              {columns.map((c) => (
                <td key={c.key} style={{ padding: '7px 10px' }}>{c.render ? c.render(row) : row[c.key]}</td>
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
    info: ['var(--info-bg)', 'var(--info)'],
    warn: ['var(--amber-bg)', 'var(--amber)'],
    error: ['var(--red-bg)', 'var(--red)'],
    ok: ['var(--green-bg)', 'var(--green)'],
  };
  const [bg, edge] = tones[tone];
  return (
    <div style={{ background: bg, borderLeft: `3px solid ${edge}`, borderRadius: '0 var(--radius) var(--radius) 0', padding: '8px 12px', fontSize: '0.8rem', lineHeight: 1.5, color: 'var(--text)' }}>
      {children}
    </div>
  );
}

export function Btn({ onClick, disabled, children, tone = 'primary', title }) {
  const styles = {
    primary: { background: 'var(--charcoal)', color: '#fff', border: '1px solid var(--charcoal)' },
    ok: { background: 'var(--green)', color: '#fff', border: '1px solid var(--green)' },
    danger: { background: 'var(--red)', color: '#fff', border: '1px solid var(--red)' },
    ghost: { background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border-strong)' },
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        ...styles[tone],
        borderRadius: 'var(--radius)',
        padding: '7px 14px',
        fontSize: '0.8rem',
        fontWeight: 600,
        fontFamily: 'inherit',
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        opacity: disabled ? 0.5 : 1,
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
