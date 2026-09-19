import React from 'react';
import { MapPin } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { Panel, Stat, StatGrid, fmt } from './ui';

const signalColor = (s) => (s === 'GREEN' ? '#10b981' : s === 'YELLOW' ? '#f59e0b' : '#ef4444');

export default function IntersectionDetailModal() {
  const { selectedIntersection: n, network, emergencyCorridorActive, emergencyRoute } = useTraffic();

  if (!n) {
    return <Panel title="JUNCTION INSPECTOR" icon={<MapPin size={18} color="#00f5ff" />}><div style={{ color: 'rgba(196,181,253,.7)', fontSize: '0.8rem' }}>Waiting for simulation data…</div></Panel>;
  }
  const onCorridor = emergencyCorridorActive && emergencyRoute.includes(n.id);

  return (
    <Panel
      title={n.name}
      icon={<MapPin size={18} color="#00f5ff" />}
      right={
        <span style={{ background: `${signalColor(n.signal)}20`, border: `1px solid ${signalColor(n.signal)}`, color: signalColor(n.signal), borderRadius: '999px', padding: '3px 10px', fontSize: '0.72rem', fontWeight: 800 }}>
          {n.signal}
        </span>
      }
    >
      <div style={{ fontSize: '0.72rem', color: '#c4b5fd' }}>
        {n.id} · {n.phase}
        {onCorridor && <span style={{ color: '#f87171', fontWeight: 700 }}> · on an ambulance route (corridor active)</span>}
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'rgba(196, 181, 253, 0.8)', marginBottom: '4px' }}>
          <span>Queue load (scale: mean queue / {network?.queue_reference_vehicles} vehicles)</span>
          <span style={{ fontWeight: 700, color: n.density > 85 ? '#ef4444' : '#00f5ff' }}>{n.density}%</span>
        </div>
        <div style={{ height: '6px', borderRadius: '3px', background: 'rgba(255,255,255,0.08)' }}>
          <div style={{ width: `${n.density}%`, height: '100%', borderRadius: '3px', background: n.density > 85 ? '#ef4444' : n.density > 55 ? '#f59e0b' : '#10b981' }} />
        </div>
      </div>

      <StatGrid min={110}>
        <Stat label="Mean queue" value={`${n.queue} veh`} sub={`starts at ${n.initialQueue}`} />
        <Stat label="Queue at end" value={n.finalQueue === undefined ? '—' : `${n.finalQueue} veh`} />
        <Stat label="Mean head wait" value={`${fmt.n(n.meanHeadWait, 0)} s`} sub="front-of-queue vehicle" />
        <Stat label="Max head wait" value={`${fmt.n(n.maxHeadWait, 0)} s`} />
        <Stat label="Green (plan in use)" value={`${n.signalDuration} s`} sub={`of ${network?.cycle_length} s cycle`} color="#a855f7" />
        <Stat label="Solver plan" value={n.optimizedDuration === undefined ? 'run optimiser' : `${n.optimizedDuration} s`} color="#10b981" />
      </StatGrid>

      <div style={{ fontSize: '0.72rem', color: 'rgba(196, 181, 253, 0.75)', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
        <span>Adjacent: <strong>{n.connectedTo.join(' ↔ ') || 'none'}</strong></span>
        <span>Arrivals: <strong>{n.arrivalRate}/s</strong></span>
        <span>Cross street: <strong>{n.crossStreetRate ? `${n.crossStreetRate}/s` : 'not modelled'}</strong></span>
        <span>Bus share: <strong>{Math.round(n.busProbability * 100)}%</strong></span>
      </div>
      <div style={{ fontSize: '0.66rem', color: 'rgba(167, 139, 250, 0.6)' }}>
        Signal colour is the simulator's cyclic rule on a looping model clock; values are simulated, not measured.
      </div>
    </Panel>
  );
}
