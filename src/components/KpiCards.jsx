import React from 'react';
import { Timer, Car, TrendingUp, Users, Scale, CloudSun, Ambulance, ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { fmt } from './ui';

const sum = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);
const meanResponse = (m) => {
  const done = (m?.emergency_vehicle_results || []).filter((v) => v.response_time !== null && v.response_time !== undefined);
  return done.length ? done.reduce((a, v) => a + v.response_time, 0) / done.length : null;
};

// Every value below is read from the simulator run shown (m) and the fixed-time baseline run (b).
export default function KpiCards() {
  const { metrics: m, baselineMetrics: b, loading, network } = useTraffic();

  if (!m || !b) {
    return (
      <div style={{ color: 'rgba(196, 181, 253, 0.7)', fontSize: '0.85rem', padding: '12px' }}>
        {loading ? 'Running the simulator…' : 'No simulation data. Is the QuantumFlow API running?'}
      </div>
    );
  }

  const horizon = network?.duration_seconds ?? 300;
  const cards = [
    { id: 'wait', title: 'Average Waiting Time', tag: 'seconds per vehicle', icon: Timer, color: '#00f5ff', v: m.average_waiting_time, base: b.average_waiting_time, lower: true, f: (x) => `${fmt.n(x)} s` },
    { id: 'queue', title: 'Mean Total Queue', tag: 'vehicles, all junctions', icon: Car, color: '#a855f7', v: sum(m.approach_mean_queue), base: sum(b.approach_mean_queue), lower: true, f: (x) => `${fmt.n(x)} veh` },
    { id: 'thru', title: 'Throughput', tag: `vehicles completed in ${horizon} s`, icon: TrendingUp, color: '#10b981', v: m.throughput, base: b.throughput, lower: false, f: (x) => fmt.int(x) },
    { id: 'pdelay', title: 'Person-Delay', tag: 'person-seconds waiting', icon: Users, color: '#f59e0b', v: m.total_person_delay, base: b.total_person_delay, lower: true, f: (x) => fmt.int(x) },
    { id: 'jain', title: 'Fairness (Jain index)', tag: '1.0 = perfectly equal', icon: Scale, color: '#38bdf8', v: m.jain_fairness_index, base: b.jain_fairness_index, lower: false, f: (x) => fmt.n(x, 3), absolute: true },
    { id: 'co2', title: 'Idling CO₂ (model)', tag: `kg over ${horizon} s`, icon: CloudSun, color: '#94a3b8', v: m.estimated_co2_kg, base: b.estimated_co2_kg, lower: true, f: (x) => `${fmt.n(x, 2)} kg` },
  ];
  const resp = meanResponse(m);
  if (resp !== null) {
    cards.push({ id: 'amb', title: 'Ambulance Response', tag: m.emergency_corridor_enabled ? 'green corridor ON' : 'no preemption', icon: Ambulance, color: m.emergency_corridor_enabled ? '#ef4444' : '#c084fc', v: resp, base: meanResponse(b), lower: true, f: (x) => `${fmt.n(x, 0)} s`, highlight: m.emergency_corridor_enabled });
  }

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', width: '100%' }}>
        {cards.map((c) => {
          const Icon = c.icon;
          const diff = c.v - c.base;
          const same = Math.abs(diff) < 1e-9;
          const better = c.lower ? diff < 0 : diff > 0;
          const changeText = same ? '0.0%' : c.absolute ? `${diff > 0 ? '+' : ''}${diff.toFixed(3)}` : fmt.pct(c.v, c.base);
          const tone = same ? '#94a3b8' : better ? '#10b981' : '#ef4444';
          const Arrow = same ? Minus : diff < 0 ? ArrowDownRight : ArrowUpRight;
          return (
            <div
              key={c.id}
              style={{
                background: c.highlight ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(20, 10, 30, 0.9) 100%)' : 'linear-gradient(135deg, rgba(18, 14, 38, 0.85) 0%, rgba(10, 8, 22, 0.92) 100%)',
                border: c.highlight ? '1px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(139, 92, 246, 0.18)',
                borderRadius: '12px',
                padding: '16px',
                backdropFilter: 'blur(12px)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div style={{ position: 'absolute', top: 0, left: '15%', width: '70%', height: '1px', background: `linear-gradient(90deg, transparent, ${c.color}, transparent)` }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'rgba(216, 207, 247, 0.7)' }}>{c.title}</div>
                  <div style={{ fontSize: '0.62rem', color: c.color, fontWeight: 700, letterSpacing: '0.04em', marginTop: '2px' }}>{c.tag}</div>
                </div>
                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(82,39,255,0.2)', border: `1px solid ${c.color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon size={16} color={c.color} />
                </div>
              </div>
              <div>
                <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>{c.f(c.v)}</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.7rem' }}>
                  <span style={{ color: 'rgba(167, 139, 250, 0.6)' }}>Fixed-time: {c.f(c.base)}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 700, color: tone }}>
                    <Arrow size={13} />
                    {changeText}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ fontSize: '0.68rem', color: 'rgba(167, 139, 250, 0.6)', marginTop: '8px' }}>
        Simulated values from the QuantumFlow backend (seed 42), compared with the fixed 30 s baseline. Green means better than baseline.
      </div>
    </div>
  );
}
