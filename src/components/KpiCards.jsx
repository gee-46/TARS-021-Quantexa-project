import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import { Panel, fmt } from './ui';

const sum = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);
const meanResponse = (m) => {
  const done = (m?.emergency_vehicle_results || []).filter((v) => v.response_time !== null && v.response_time !== undefined);
  return done.length ? done.reduce((a, v) => a + v.response_time, 0) / done.length : null;
};

// Operational metrics: the run shown vs the fixed 30 s baseline run. Every value is read from the simulator.
export default function KpiCards() {
  const { metrics: m, baselineMetrics: b, loading, network } = useTraffic();

  if (!m || !b) {
    return <Panel title="Operational metrics"><div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>{loading ? 'Running the simulator…' : 'No simulation data. Is the QuantumFlow API running?'}</div></Panel>;
  }

  const horizon = network?.duration_seconds ?? 300;
  const rows = [
    { id: 'wait', label: 'Average waiting time', unit: 's / vehicle', v: m.average_waiting_time, base: b.average_waiting_time, lower: true, f: (x) => fmt.n(x) },
    { id: 'queue', label: 'Mean total queue', unit: 'vehicles', v: sum(m.approach_mean_queue), base: sum(b.approach_mean_queue), lower: true, f: (x) => fmt.n(x) },
    { id: 'thru', label: 'Throughput', unit: `vehicles / ${horizon} s`, v: m.throughput, base: b.throughput, lower: false, f: (x) => fmt.int(x) },
    { id: 'pdelay', label: 'Person-delay', unit: 'person-seconds', v: m.total_person_delay, base: b.total_person_delay, lower: true, f: (x) => fmt.int(x) },
    { id: 'jain', label: 'Fairness (Jain index)', unit: '1.0 = equal', v: m.jain_fairness_index, base: b.jain_fairness_index, lower: false, f: (x) => fmt.n(x, 3), absolute: true },
    { id: 'co2', label: 'Idling CO₂ (model)', unit: `kg / ${horizon} s`, v: m.estimated_co2_kg, base: b.estimated_co2_kg, lower: true, f: (x) => fmt.n(x, 2) },
  ];
  const resp = meanResponse(m);
  if (resp !== null) {
    rows.push({ id: 'amb', label: 'Ambulance response', unit: m.emergency_corridor_enabled ? 'corridor on' : 'no preemption', v: resp, base: meanResponse(b), lower: true, f: (x) => fmt.n(x, 0) });
  }

  return (
    <Panel title="Operational metrics" right={<span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>vs fixed 30 s plan · simulated, seed 42</span>}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 10 }}>
        {rows.map((r) => {
          const diff = r.v - r.base;
          const same = Math.abs(diff) < 1e-9;
          const better = r.lower ? diff < 0 : diff > 0;
          const tone = same ? 'var(--muted)' : better ? 'var(--green)' : 'var(--red)';
          const delta = same ? 'no change' : r.absolute ? `${diff > 0 ? '+' : ''}${diff.toFixed(3)}` : fmt.pct(r.v, r.base);
          return (
            <div key={r.id} style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '8px 10px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600 }}>{r.label}</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 2 }}>
                <span style={{ fontSize: '1.2rem', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{r.f(r.v)}</span>
                <span style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{r.unit}</span>
              </div>
              <div style={{ fontSize: '0.7rem', display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
                <span style={{ color: 'var(--muted)' }}>baseline {r.f(r.base)}</span>
                <strong style={{ color: tone }}>{delta}</strong>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
