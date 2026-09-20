import React from 'react';
import { Network, CheckCircle2, RotateCcw, Cpu } from 'lucide-react';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import IntersectionDetailModal from '../components/IntersectionDetailModal';
import JunctionCharts from '../components/JunctionCharts';
import { useTraffic } from '../context/TrafficContext';
import { PageHeader, Panel, DataTable, Btn } from '../components/ui';

const Sig = ({ s }) => <strong style={{ color: s === 'GREEN' ? 'var(--green)' : 'var(--red)' }}>● {s}</strong>;

export default function TrafficNetworkPage() {
  const { intersections, isOptimized, isOptimizing, optimizationResult, handleRunOptimization, handleApplyOptimization, handleResetSignals, selectedIntersectionId, setSelectedIntersectionId } = useTraffic();
  const rows = Object.values(intersections).map((n) => ({ id: n.id, ...n }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, width: '100%' }}>
      <PageHeader
        icon={<Network size={20} />}
        title="Junctions & signal control"
        subtitle="Four-junction arterial (I1 → I4): simulated queues, waits and the signal plan in use."
        right={
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Btn onClick={handleRunOptimization} disabled={isOptimizing}><Cpu size={14} /> {isOptimizing ? 'Solving…' : 'Run QUBO optimiser'}</Btn>
            <Btn onClick={handleApplyOptimization} disabled={!optimizationResult || isOptimized} tone="ok"><CheckCircle2 size={14} /> Apply optimised signals</Btn>
            <Btn onClick={handleResetSignals} tone="ghost"><RotateCcw size={14} /> Reset</Btn>
          </div>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(300px, 1fr)', gap: 14, alignItems: 'start' }}>
        <TrafficNetworkVisualizer />
        <IntersectionDetailModal />
      </div>

      <Panel title="Signal control table" right={<span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>{isOptimized ? 'Solver-chosen plan applied (simulated)' : 'Fixed 30 s plan active'}</span>}>
        <DataTable
          columns={[
            { key: 'id', label: 'Junction', render: (n) => <strong>{n.id} · {n.name}</strong> },
            { key: 'signal', label: 'Signal now', render: (n) => <Sig s={n.signal} /> },
            { key: 'dur', label: 'Green in use', render: (n) => `${n.signalDuration} s` },
            { key: 'opt', label: 'Solver green', render: (n) => (n.optimizedDuration === undefined ? <span style={{ color: 'var(--muted)' }}>run optimiser</span> : <strong style={{ color: 'var(--green)' }}>{n.optimizedDuration} s</strong>) },
            { key: 'queue', label: 'Mean queue', render: (n) => <span style={{ color: n.queue > 30 ? 'var(--red)' : 'inherit', fontWeight: 600 }}>{n.queue} veh</span> },
            { key: 'load', label: 'Queue load', render: (n) => <span style={{ color: n.density > 80 ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>{n.density}%</span> },
            { key: 'act', label: '', render: (n) => <Btn tone="ghost" onClick={() => setSelectedIntersectionId(n.id)} disabled={selectedIntersectionId === n.id}>Inspect</Btn> },
          ]}
          rows={rows}
        />
      </Panel>

      <JunctionCharts />
    </div>
  );
}
