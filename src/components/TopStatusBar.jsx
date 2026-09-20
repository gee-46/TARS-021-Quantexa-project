import React from 'react';
import { X } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';

function Chip({ label, value, tone }) {
  const color = { green: '#7be0a0', red: '#ff8a80', amber: '#ffcc66', info: '#9cc4f5' }[tone] || '#e6e9ec';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15, padding: '0 14px', borderLeft: '1px solid rgba(255,255,255,0.14)' }}>
      <span style={{ fontSize: '0.6rem', letterSpacing: '0.08em', color: '#9aa4af', fontWeight: 600 }}>{label}</span>
      <strong style={{ fontSize: '0.8rem', color, letterSpacing: '0.03em' }}>{value}</strong>
    </div>
  );
}

function SignalMark() {
  return (
    <svg width="22" height="30" viewBox="0 0 22 30" aria-hidden="true">
      <rect x="4" y="1" width="14" height="28" rx="4" fill="#1a1d22" stroke="#8b949e" />
      <circle cx="11" cy="8" r="3.4" fill="#e5484d" />
      <circle cx="11" cy="15" r="3.4" fill="#f2b632" />
      <circle cx="11" cy="22" r="3.4" fill="#3ddc84" />
    </svg>
  );
}

export default function TopStatusBar() {
  const { systemStatus, simulationTime, storyPhase, emergencyCorridorActive, latestNotification, dismissNotification, scenarios, scenarioId, selectScenario, network, backend, loading, hasAmbulances } = useTraffic();

  const online = backend.status === 'online';
  const corridorOn = emergencyCorridorActive || ['activating', 'clearing', 'done'].includes(storyPhase);
  const emergency = !hasAmbulances ? ['N/A', null] : corridorOn ? ['ACTIVE', 'green'] : storyPhase === 'stuck' ? ['REQUESTED', 'red'] : ['READY', 'info'];

  return (
    <>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, minHeight: 54, padding: '0 16px', background: 'var(--charcoal)', color: '#fff', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SignalMark />
          <div style={{ lineHeight: 1.15 }}>
            <div style={{ fontSize: '0.98rem', fontWeight: 700, letterSpacing: '0.02em' }}>QuantumFlow</div>
            <div style={{ fontSize: '0.66rem', color: '#9aa4af', letterSpacing: '0.09em' }}>URBAN TRAFFIC OPERATIONS CENTER</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', rowGap: 6 }}>
          <Chip label="SYSTEM" value={online ? 'ONLINE' : systemStatus} tone={online ? 'green' : 'red'} />
          <Chip label="SIMULATION" value={online ? (loading ? 'LOADING' : 'ACTIVE') : 'OFFLINE'} tone={online ? (loading ? 'amber' : 'green') : 'red'} />
          <Chip label="EMERGENCY MODE" value={emergency[0]} tone={emergency[1]} />
          <Chip label="JUNCTIONS" value={network?.nodes?.length ?? '—'} />
          <Chip label="MODEL CLOCK" value={simulationTime} />
          <div style={{ paddingLeft: 14, borderLeft: '1px solid rgba(255,255,255,0.14)' }}>
            <select
              value={scenarioId}
              disabled={loading || scenarios.length === 0}
              onChange={(e) => selectScenario(e.target.value)}
              aria-label="Scenario"
              style={{ background: '#3a4049', color: '#fff', border: '1px solid #59616c', borderRadius: 4, padding: '5px 8px', fontSize: '0.78rem', maxWidth: 270, fontFamily: 'inherit' }}
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {backend.status === 'offline' && (
        <div style={{ background: 'var(--red)', color: '#fff', fontSize: '0.78rem', padding: '6px 16px' }}>QuantumFlow API unreachable: {backend.error}</div>
      )}
      {network?.disclaimer && (
        <div style={{ background: 'var(--amber-bg)', color: 'var(--amber)', fontSize: '0.74rem', padding: '5px 16px', borderBottom: '1px solid #f0d9a8' }}>{network.disclaimer}</div>
      )}

      {latestNotification && (
        <div style={{ position: 'fixed', top: 62, right: 16, zIndex: 50, maxWidth: 380, display: 'flex', gap: 10, alignItems: 'flex-start', padding: '10px 12px', background: 'var(--surface)', border: '1px solid var(--border-strong)', borderLeft: `4px solid ${latestNotification.type === 'ERROR' || latestNotification.type === 'EMERGENCY' ? 'var(--red)' : latestNotification.type === 'WARNING' ? 'var(--amber)' : 'var(--info)'}`, borderRadius: 4, boxShadow: '0 4px 14px rgba(0,0,0,0.15)', animation: 'slideIn 0.25s ease-out' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700 }}>{latestNotification.title}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginTop: 2 }}>{latestNotification.message}</div>
          </div>
          <button onClick={dismissNotification} aria-label="Dismiss" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={16} /></button>
        </div>
      )}
    </>
  );
}
