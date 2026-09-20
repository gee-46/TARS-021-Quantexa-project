import React from 'react';
import { Siren, Scale } from 'lucide-react';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import EmergencyCorridorPanel from '../components/EmergencyCorridorPanel';
import DispatchPanel from '../components/DispatchPanel';
import { useTraffic } from '../context/TrafficContext';
import { PageHeader, Panel, DataTable, Note, fmt } from '../components/ui';

export default function EmergencyCorridorPage() {
  const { emergencyResult, hasAmbulances, emergencyCorridorActive } = useTraffic();
  const arb = emergencyResult?.conflict_arbiter;
  const events = (emergencyResult?.with_corridor?.corridor_event_log || []).filter((e) => /Conflict|activated|released|completed/i.test(e.message));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<Siren size={24} color="#c62828" />}
        title="EMERGENCY CORRIDOR & CONFLICT RESOLUTION"
        subtitle="When two ambulances need the same junction, a small QUBO sequences them; QAOA, SA and Greedy are compared on it."
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        <TrafficNetworkVisualizer />
        <EmergencyCorridorPanel />
      </div>

      <DispatchPanel />

      {hasAmbulances && !emergencyCorridorActive && !emergencyResult && (
        <Note>Press “Simulate green corridor” to run the same traffic with and without preemption and, for conflicting routes, solve the sequencing QUBO.</Note>
      )}

      {arb && (
        <Panel title={`CONFLICT QUBO AT ${arb.conflict_intersection} — ${arb.num_qubits} QUBITS`} icon={<Scale size={18} color="#2a2f36" />}>
          <DataTable
            columns={[
              { key: 'solver', label: 'Solver', render: (r) => <strong>{r.solver_name.toUpperCase()}</strong> },
              { key: 'order', label: 'Order', render: (r) => (r.sequence.length ? r.sequence.join(' → ') : 'invalid') },
              { key: 'energy', label: 'Energy', render: (r) => fmt.n(r.energy, 2) },
              { key: 'opt', label: 'Optimal?', render: (r) => (r.is_optimal ? 'yes' : 'no') },
              { key: 'rt', label: 'Runtime', render: (r) => `${fmt.n(r.runtime_seconds, 3)} s` },
              { key: 'note', label: 'Note', render: (r) => <span style={{ color: 'var(--muted)' }}>{r.note}</span> },
            ]}
            rows={Object.values(arb.records).map((r) => ({ id: r.solver_name, ...r }))}
          />
          <Note tone="ok">{arb.verdict} Exact optimum energy: {fmt.n(arb.exact_energy, 2)} (exhaustive enumeration). QAOA runs on the Aer simulator; no quantum advantage is claimed.</Note>
        </Panel>
      )}

      {events.length > 0 && (
        <Panel title="CORRIDOR EVENT LOG (SIMULATOR)">
          <DataTable
            columns={[
              { key: 'timestamp', label: 'Sim t (s)' },
              { key: 'event_type', label: 'Event' },
              { key: 'message', label: 'Detail' },
            ]}
            rows={events.slice(0, 14)}
          />
        </Panel>
      )}
    </div>
  );
}
