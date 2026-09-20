import React, { useState } from 'react';
import { Cpu, Play, CheckCircle2, RotateCcw, HelpCircle, Circle, Loader } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import QuboExplanationModal from './QuboExplanationModal';
import { Panel, Btn, StatGrid, Stat, Note } from './ui';

// Signal optimisation control: same context handlers as before (run / apply / reset), operational presentation.
export default function OptimizationPipeline() {
  const { isOptimizing, optimizationResult: r, isOptimized, handleRunOptimization, handleApplyOptimization, handleResetSignals, network } = useTraffic();
  const [showModal, setShowModal] = useState(false);

  const steps = [
    { done: !!network, text: `Traffic state collected (${network?.nodes?.length ?? '—'} junctions, ${network?.edges?.length ?? '—'} arterial links)` },
    { done: !!network, text: 'Upstream/downstream couplings encoded in the QUBO' },
    { done: !!r, text: `QUBO formulated (${r?.qubo?.variables ?? 12} binary variables: 4 junctions × 3 green durations)` },
    { done: !!r, running: isOptimizing, text: isOptimizing ? 'Solving with QAOA (Aer simulator), simulated annealing and greedy…' : r ? `Solved: best solver ${r.best_solver.toUpperCase()}` : 'Waiting to solve' },
    { done: !!r, text: r ? `Signal plan ${Object.entries(r.best_plan).map(([k, v]) => `${k}:${v}s`).join('  ')} (QUBO energy ${r.best_energy.toFixed(2)})` : 'Signal plan not generated yet' },
  ];

  return (
    <Panel title="Signal optimisation" icon={<Cpu size={15} />} right={<Btn tone="ghost" onClick={() => setShowModal(true)}><HelpCircle size={14} /> What is optimised?</Btn>}>
      <StatGrid min={120}>
        <Stat label="Method" value="QAOA · SA · Greedy" />
        <Stat label="Formulation" value="QUBO / Ising" />
        <Stat label="Variables" value={`${r?.qubo?.variables ?? 12} binary`} />
        <Stat label="Backend" value="Qiskit Aer simulator" />
      </StatGrid>

      <ol style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((s, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem', color: s.done ? 'var(--text)' : 'var(--muted)' }}>
            {s.running ? <Loader size={14} className="spin" color="var(--info)" /> : s.done ? <CheckCircle2 size={14} color="var(--green)" /> : <Circle size={14} />}
            <span>{s.text}</span>
          </li>
        ))}
      </ol>

      {r && <Note tone="ok">{r.verdict}</Note>}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Btn onClick={handleRunOptimization} disabled={isOptimizing}><Play size={14} /> {isOptimizing ? 'Solving…' : 'Run optimisation'}</Btn>
        <Btn onClick={handleApplyOptimization} disabled={!r || isOptimized} tone="ok"><CheckCircle2 size={14} /> Apply optimised signals</Btn>
        <Btn onClick={handleResetSignals} tone="ghost" title="Back to the fixed 30 s plan"><RotateCcw size={14} /> Reset</Btn>
      </div>
      {showModal && <QuboExplanationModal onClose={() => setShowModal(false)} />}
    </Panel>
  );
}
