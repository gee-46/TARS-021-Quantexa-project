import React from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, Cpu, Siren, BarChart3, GitCompare, Network, Map, Share2, Layers, AlertTriangle } from 'lucide-react';

// Operational workflow: live picture -> optimisation -> emergency -> analytics -> system. All existing routes are kept.
const GROUPS = [
  { title: 'Live traffic', items: [{ path: '/dashboard', label: 'Live traffic', icon: Activity }] },
  {
    title: 'Optimisation',
    items: [
      { path: '/quantum', label: 'Signal optimisation', icon: Cpu },
      { path: '/comparison', label: 'Solver comparison', icon: GitCompare },
    ],
  },
  {
    title: 'Emergency mode',
    items: [
      { path: '/emergency', label: 'Emergency corridor', icon: Siren },
      { path: '/events', label: 'Scenarios & events', icon: AlertTriangle },
    ],
  },
  { title: 'Analytics', items: [{ path: '/analytics', label: 'Analytics & trade-offs', icon: BarChart3 }] },
  {
    title: 'System / network',
    items: [
      { path: '/traffic', label: 'Junctions & signals', icon: Network },
      { path: '/map', label: 'Corridor map', icon: Map },
      { path: '/graph', label: 'Network graph', icon: Share2 },
      { path: '/architecture', label: 'System architecture', icon: Layers },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside style={{ width: 212, flexShrink: 0, background: 'var(--surface)', borderRight: '1px solid var(--border)', overflowY: 'auto', padding: '10px 0' }}>
      <nav aria-label="Sections">
        {GROUPS.map((g) => (
          <div key={g.title} style={{ marginBottom: 8 }}>
            <div style={{ padding: '8px 16px 4px', fontSize: '0.64rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--muted)' }}>{g.title}</div>
            {g.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '7px 16px',
                    fontSize: '0.84rem',
                    fontWeight: isActive ? 700 : 500,
                    textDecoration: 'none',
                    color: isActive ? 'var(--text)' : 'var(--text-2)',
                    background: isActive ? 'var(--surface-3)' : 'transparent',
                    borderLeft: `3px solid ${isActive ? 'var(--charcoal)' : 'transparent'}`,
                  })}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
