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
      title="EMERGENCY GREEN CORRIDOR"
      icon={<Ambulance size={20} color="#ef4444" />}
      right={emergencyCorridorActive && <span style={{ color: '#ef4444', fontWeight: 800, fontSize: '0.72rem' }}>● PREEMPTION ON (simulated)</span>}
      style={emergencyCorridorActive ? { border: '1px solid rgba(239, 68, 68, 0.5)' } : undefined}
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
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    {r.a.route.map((n, i) => (
                      <React.Fragment key={n}>
                        {i > 0 && <ArrowRight size={11} color="rgba(139,92,246,.6)" />}
                        <span style={{ color: emergencyCorridorActive ? '#6ee7b7' : '#c4b5fd' }}>{n}</span>
                      </React.Fragment>
                    ))}
                  </span>
                ),
              },
              { key: 'off', label: 'Response, no corridor', render: (r) => (r.off === null || r.off === undefined ? '—' : `${fmt.n(r.off, 0)} s`) },
              { key: 'on', label: 'Response, corridor', render: (r) => (r.on === undefined ? 'not run yet' : r.on === null ? 'unfinished' : <strong style={{ color: '#6ee7b7' }}>{fmt.n(r.on, 0)} s</strong>) },
            ]}
            rows={rows}
          />
          <div style={{ display: 'flex', gap: '10px' }}>
            {!emergencyCorridorActive ? (
              <Btn onClick={handleActivateCorridor} disabled={emergencyBusy}>
                <Zap size={16} />
                {emergencyBusy ? 'Simulating…' : 'SIMULATE GREEN CORRIDOR'}
              </Btn>
            ) : (
              <Btn onClick={handleRestoreTraffic} tone="ghost">
                <RotateCcw size={16} />
                SHOW WITHOUT CORRIDOR
              </Btn>
            )}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'rgba(167, 139, 250, 0.65)' }}>
            Preemption forces the whole junction green; turn phases are not modelled. Times are simulated seconds.
          </div>
        </>
      )}
    </Panel>
  );
}
