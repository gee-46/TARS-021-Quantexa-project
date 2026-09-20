import React, { useMemo } from 'react';
import { useTraffic } from '../context/TrafficContext';
import TrafficScene from './TrafficScene';
import { frameLive } from '../services/storyModel';

// Current network state on the same road-network renderer as the live screen (queues, signals, ambulance routes).
export default function TrafficNetworkVisualizer() {
  const { network, metrics, currentPlan, clock, emergencyCorridorActive, emergencyRoutes, selectedIntersectionId, setSelectedIntersectionId, loading } = useTraffic();

  const frame = useMemo(
    () => frameLive({ network, metrics, plan: currentPlan, clock, corridorActive: emergencyCorridorActive, routes: emergencyRoutes }),
    [network, metrics, currentPlan, clock, emergencyCorridorActive, emergencyRoutes],
  );

  if (!frame) {
    return <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', background: 'var(--surface)', padding: 16, color: 'var(--muted)' }}>{loading ? 'Loading network…' : 'No network data.'}</div>;
  }
  const names = Object.fromEntries(network.nodes.map((n) => [n.id, n.name]));
  const labels = Object.fromEntries(frame.ids.map((id) => [id, `Queue ${Math.round(frame.queues[id])} veh`]));
  const dirOf = (r) => (frame.xs[r.route[r.route.length - 1]] >= frame.xs[r.route[0]] ? 1 : -1);

  return (
    <section style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden', background: 'var(--surface)' }}>
      <TrafficScene
        ids={frame.ids} xs={frame.xs} names={names} signals={frame.signals} cars={frame.cars}
        ambulances={frame.ambs.map((a) => ({ id: a.id, x: a.x, y: a.y, dir: a.dir, label: a.id }))}
        routes={frame.routes.map((r) => ({ id: r.id, route: r.route, dir: dirOf(r) }))}
        corridor={emergencyCorridorActive} queueLabels={labels} unit={frame.unit}
      />
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', padding: '8px 12px', borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--muted)', letterSpacing: '0.06em' }}>INSPECT JUNCTION</span>
        {frame.ids.map((id) => (
          <button
            key={id}
            onClick={() => setSelectedIntersectionId(id)}
            aria-pressed={selectedIntersectionId === id}
            style={{ padding: '3px 12px', fontSize: '0.78rem', fontWeight: 700, fontFamily: 'inherit', cursor: 'pointer', borderRadius: 4, border: '1px solid var(--border-strong)', background: selectedIntersectionId === id ? 'var(--charcoal)' : 'var(--surface)', color: selectedIntersectionId === id ? '#fff' : 'var(--text)' }}
          >
            {id}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--muted)' }}>Simulated queues and signals; vehicle icons are schematic{frame.unit > 1 ? ` (1 icon = ${frame.unit} vehicles)` : ''}.</span>
      </div>
    </section>
  );
}
