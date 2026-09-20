import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  Cpu,
  Siren,
  AlertTriangle,
  BarChart3,
  GitCompare,
  Layers,
  Map,
  Share2,
  Sparkles,
  Radio,
  ArrowLeft,
} from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';

const navItems = [
  { path: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { path: '/traffic', label: 'Traffic Network', icon: Network },
  { path: '/map', label: 'Corridor Map', icon: Map },
  { path: '/graph', label: 'Network Graph', icon: Share2 },
  { path: '/quantum', label: 'Quantum Optimizer', icon: Cpu },
  { path: '/emergency', label: 'Emergency Corridor', icon: Siren },
  { path: '/events', label: 'Scenarios & Events', icon: AlertTriangle },
  { path: '/analytics', label: 'Analytics & Trade-offs', icon: BarChart3 },
  { path: '/comparison', label: 'Solver Comparison', icon: GitCompare },
  { path: '/architecture', label: 'System Architecture', icon: Layers },
];

export default function Sidebar() {
  const { systemStatus, quantumEngineStatus } = useTraffic();

  return (
    <aside style={{
      width: '260px',
      minWidth: '260px',
      height: '100vh',
      background: 'linear-gradient(180deg, rgba(12, 10, 26, 0.95) 0%, rgba(6, 5, 15, 0.98) 100%)',
      borderRight: '1px solid rgba(139, 92, 246, 0.15)',
      display: 'flex',
      flexDirection: 'column',
      backdropFilter: 'blur(20px)',
      zIndex: 40,
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid rgba(139, 92, 246, 0.12)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #5227FF 0%, #A855F7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(168, 85, 247, 0.5)',
            }}>
              <Sparkles size={18} color="#fff" />
            </div>
            <div>
              <div style={{
                fontSize: '1.05rem',
                fontWeight: 800,
                color: '#fff',
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
              }}>
                QuantumForce
              </div>
              <div style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: '#a78bfa',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}>
                Traffic Control Center
              </div>
            </div>
          </div>
        </div>

        <Link
          to="/"
          style={{
            marginTop: '8px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: 'rgba(196, 181, 253, 0.7)',
            textDecoration: 'none',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(196, 181, 253, 0.7)')}
        >
          <ArrowLeft size={12} /> Return to Landing Experience
        </Link>
      </div>

      {/* Navigation Items */}
      <nav style={{
        flex: 1,
        padding: '16px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        overflowY: 'auto',
      }}>
        <div style={{
          fontSize: '0.65rem',
          fontWeight: 700,
          color: 'rgba(167, 139, 250, 0.5)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          padding: '6px 12px',
        }}>
          Operations Command
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#fff' : 'rgba(216, 207, 247, 0.75)',
                background: isActive
                  ? 'linear-gradient(90deg, rgba(82, 39, 255, 0.25) 0%, rgba(168, 85, 247, 0.15) 100%)'
                  : 'transparent',
                border: isActive
                  ? '1px solid rgba(168, 85, 247, 0.35)'
                  : '1px solid transparent',
                textDecoration: 'none',
                transition: 'all 0.18s ease',
              })}
            >
              <Icon size={17} style={{ color: '#a855f7' }} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* System Status Telemetry Footer */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid rgba(139, 92, 246, 0.12)',
        background: 'rgba(0, 0, 0, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}>
        <div style={{
          fontSize: '0.65rem',
          fontWeight: 700,
          color: 'rgba(167, 139, 250, 0.6)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <Radio size={12} color="#00f5ff" /> Live Telemetry
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
          <span style={{ color: 'rgba(216, 207, 247, 0.7)' }}>System Status</span>
          <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            {systemStatus}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
          <span style={{ color: 'rgba(216, 207, 247, 0.7)' }}>Quantum Engine</span>
          <span style={{ color: '#a855f7', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#a855f7', boxShadow: '0 0 8px #a855f7' }} />
            {quantumEngineStatus}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
          <span style={{ color: 'rgba(216, 207, 247, 0.7)' }}>Simulation</span>
          <span style={{ color: '#00f5ff', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00f5ff', boxShadow: '0 0 8px #00f5ff' }} />
            RUNNING
          </span>
        </div>
      </div>
    </aside>
  );
}
