import React from 'react';
import { Ambulance, RotateCcw, ArrowRight, Zap } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { Panel, DataTable, Note, Btn, fmt } from './ui';

// Response times come from two real simulator runs (same plan, same seed): corridor OFF vs ON.
export default function EmergencyCorridorPanel() {
  const { emergencyCorridorActive, emergencyBusy, hasAmbulances, network, emergencyResult, handleActivateCorridor, handleRestoreTraffic, baselineMetrics } = useTraffic();

  const rows = (network?.ambulances || []).map((a) => {
    const off = (emergencyResult?.without_corridor || baselineMetrics)?.emergency_vehicle_results?.find((v) => v.vehicle_id === a.vehicle_id);
    const on = emergencyResult?.with_corridor?.emergency_vehicle_results?.find((v) => v.vehicle_id === a.vehicle_id);
    return { id: a.vehicle_id, a, off: off?.response_time, on: on?.response_time };
  });

  return (
    <Panel
      title="Emergency green corridor"
      icon={<Ambulance size={15} />}
      right={emergencyCorridorActive && <strong style={{ color: 'var(--green)', fontSize: '0.72rem' }}>● CORRIDOR ENABLED (simulated)</strong>}
    >
      {!hasAmbulances ? (
        <Note tone="warn">This scenario has no emergency vehicle. Choose scenario D, E, F or a Belagavi-inspired two-ambulance scenario in the header.</Note>
      ) : (
        <>
          <DataTable
            columns={[
              { key: 'vehicle', label: 'Vehicle', render: (r) => <strong>{r.a.vehicle_id}</strong> },
              { key: 'priority', label: 'Priority', render: (r) => r.a.priority },
              {
                key: 'route',
                label: 'Route',
                render: (r) => (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {r.a.route.map((n, i) => (
                      <React.Fragment key={n}>
                        {i > 0 && <ArrowRight size={11} color="var(--muted)" />}
                        <span style={{ fontWeight: 600, color: emergencyCorridorActive ? 'var(--green)' : 'var(--text)' }}>{n}</span>
                      </React.Fragment>
                    ))}
                  </span>
                ),
              },
              { key: 'off', label: 'No corridor', render: (r) => (r.off === null || r.off === undefined ? '—' : <span style={{ color: 'var(--red)', fontWeight: 600 }}>{fmt.n(r.off, 0)} s</span>) },
              { key: 'on', label: 'Corridor', render: (r) => (r.on === undefined ? 'not run yet' : r.on === null ? 'unfinished' : <strong style={{ color: 'var(--green)' }}>{fmt.n(r.on, 0)} s</strong>) },
            ]}
            rows={rows}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            {!emergencyCorridorActive ? (
              <Btn onClick={handleActivateCorridor} disabled={emergencyBusy} tone="ok">
                <Zap size={14} />
                {emergencyBusy ? 'Simulating…' : 'Simulate green corridor'}
              </Btn>
            ) : (
              <Btn onClick={handleRestoreTraffic} tone="ghost">
                <RotateCcw size={14} />
                Show without corridor
              </Btn>
            )}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>Preemption forces the whole junction green; turn phases are not modelled. Times are simulated seconds.</div>
        </>
      )}
    </Panel>
  );
}
