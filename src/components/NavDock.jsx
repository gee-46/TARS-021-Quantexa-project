import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Activity, Cpu, Siren, BarChart3, Network, Layers, RefreshCw } from 'lucide-react';

// Bottom-centre navigation dock. It only changes HOW the existing pages are reached: the routes in App.jsx are untouched
// and every page that the old sidebar linked to is still one click (or two, via the group popover) away.
const GROUPS = [
  { id: 'live', label: 'Live Traffic', icon: Activity, items: [{ path: '/dashboard', label: 'Live traffic', alias: ['/'] }] },
  { id: 'opt', label: 'Optimisation', icon: Cpu, items: [{ path: '/quantum', label: 'Signal optimisation' }, { path: '/comparison', label: 'Solver comparison' }] },
  { id: 'emg', label: 'Emergency', icon: Siren, items: [{ path: '/emergency', label: 'Emergency corridor' }, { path: '/events', label: 'Scenarios & events' }] },
  { id: 'ana', label: 'Analytics', icon: BarChart3, items: [{ path: '/analytics', label: 'Analytics & trade-offs' }] },
  { id: 'net', label: 'Network', icon: Network, items: [{ path: '/traffic', label: 'Junctions & signals' }, { path: '/map', label: 'Corridor map' }, { path: '/graph', label: 'Network graph' }] },
  { id: 'sys', label: 'System', icon: Layers, items: [{ path: '/architecture', label: 'System architecture' }], replay: true },
];

const inGroup = (g, pathname) => g.items.some((i) => i.path === pathname || (i.alias || []).includes(pathname));

export default function NavDock() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(null);
  const ref = useRef(null);

  useEffect(() => setOpen(null), [pathname]);
  useEffect(() => {
    const away = (e) => ref.current && !ref.current.contains(e.target) && setOpen(null);
    const esc = (e) => e.key === 'Escape' && setOpen(null);
    document.addEventListener('mousedown', away);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', away);
      document.removeEventListener('keydown', esc);
    };
  }, []);

  return (
    <nav ref={ref} className="nav-dock" aria-label="Sections">
      {GROUPS.map((g) => {
        const Icon = g.icon;
        const active = inGroup(g, pathname);
        const multi = g.items.length > 1 || g.replay;
        const body = (
          <>
            <Icon size={18} strokeWidth={active ? 2.3 : 1.9} />
            <span className="nav-dock-label">{g.label}</span>
          </>
        );
        return (
          <div key={g.id} className="nav-dock-cell">
            {multi ? (
              <button
                type="button"
                className={`nav-dock-item${active ? ' active' : ''}`}
                aria-haspopup="menu"
                aria-expanded={open === g.id}
                data-group={g.id}
                onClick={() => setOpen(open === g.id ? null : g.id)}
              >
                {body}
              </button>
            ) : (
              <NavLink to={g.items[0].path} data-group={g.id} className={`nav-dock-item${active ? ' active' : ''}`} aria-current={active ? 'page' : undefined}>
                {body}
              </NavLink>
            )}
            {multi && open === g.id && (
              <div className="nav-dock-menu" role="menu">
                {g.items.map((i) => (
                  <NavLink key={i.path} to={i.path} role="menuitem" className={({ isActive }) => `nav-dock-link${isActive ? ' active' : ''}`}>
                    {i.label}
                  </NavLink>
                ))}
                {g.replay && (
                  <button type="button" role="menuitem" className="nav-dock-link" onClick={() => { window.location.href = `${window.location.pathname}?loader=1`; }}>
                    <RefreshCw size={13} style={{ marginRight: 6, verticalAlign: '-2px' }} />Replay intro animation
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
