import React from 'react';
import { MapPin } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { Panel, Stat, StatGrid, fmt } from './ui';

export default function IntersectionDetailModal() {
  const { selectedIntersection: n, network, emergencyCorridorActive, emergencyRoute } = useTraffic();

  if (!n) {
    return <Panel title="Junction inspector" icon={<MapPin size={15} />}><div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Waiting for simulation data…</div></Panel>;
  }
  const onCorridor = emergencyCorridorActive && emergencyRoute.includes(n.id);
  const green = n.signal === 'GREEN';

  return (
    <Panel
      title={`${n.id} · ${n.name}`}
      icon={<MapPin size={15} />}
      right={<strong style={{ fontSize: '0.74rem', color: green ? 'var(--green)' : 'var(--red)' }}>● {n.signal}</strong>}
    >
      <div style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>
        {n.phase}
        {onCorridor && <strong style={{ color: 'var(--green)' }}> · on an ambulance route (corridor active)</strong>}
      </div>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--muted)', marginBottom: 3 }}>
          <span>Queue load (mean queue / {network?.queue_reference_vehicles} vehicles)</span>
          <strong style={{ color: n.density > 85 ? 'var(--red)' : 'var(--text)' }}>{n.density}%</strong>
        </div>
        <div style={{ height: 8, borderRadius: 4, background: 'var(--surface-3)' }}>
          <div style={{ width: `${n.density}%`, height: '100%', borderRadius: 4, background: n.density > 85 ? 'var(--red)' : n.density > 55 ? '#e0a100' : 'var(--green)' }} />
        </div>
      </div>
      <StatGrid min={110}>
        <Stat label="Mean queue" value={`${n.queue} veh`} sub={`starts at ${n.initialQueue}`} />
        <Stat label="Queue at end" value={n.finalQueue === undefined ? '—' : `${n.finalQueue} veh`} />
        <Stat label="Mean head wait" value={`${fmt.n(n.meanHeadWait, 0)} s`} sub="front-of-queue" />
        <Stat label="Max head wait" value={`${fmt.n(n.maxHeadWait, 0)} s`} />
        <Stat label="Green (plan)" value={`${n.signalDuration} s`} sub={`of ${network?.cycle_length} s cycle`} />
        <Stat label="Solver plan" value={n.optimizedDuration === undefined ? 'run optimiser' : `${n.optimizedDuration} s`} color="var(--green)" />
      </StatGrid>
      <div style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        <span>Adjacent: <strong>{n.connectedTo.join(' ↔ ') || 'none'}</strong></span>
        <span>Arrivals: <strong>{n.arrivalRate}/s</strong></span>
        <span>Cross street: <strong>{n.crossStreetRate ? `${n.crossStreetRate}/s` : 'not modelled'}</strong></span>
        <span>Bus share: <strong>{Math.round(n.busProbability * 100)}%</strong></span>
      </div>
    </Panel>
  );
}
