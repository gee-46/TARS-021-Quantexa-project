import React, { useState } from 'react';
import { Cpu, Zap, Layers, HelpCircle, Activity } from 'lucide-react';
import OptimizationPipeline from '../components/OptimizationPipeline';
import QuboExplanationModal from '../components/QuboExplanationModal';
import { useTraffic } from '../context/TrafficContext';
import { runNoise } from '../services/api';
import { PageHeader, Panel, DataTable, Note, Btn, Stat, StatGrid, fmt } from '../components/ui';

const planText = (p) => Object.entries(p || {}).map(([k, v]) => `${k}:${v}s`).join('  ');

export default function QuantumOptimizerPage() {
  const { optimizationResult: r, scenarioId, seed, network, notify } = useTraffic();
  const [showModal, setShowModal] = useState(false);
  const [noise, setNoise] = useState(null);
  const [noiseBusy, setNoiseBusy] = useState(false);
  const [noiseError, setNoiseError] = useState(null);

  const canNoise = (network?.ambulances?.length || 0) >= 2;
  const doNoise = async () => {
    setNoiseBusy(true);
    setNoiseError(null);
    try {
      setNoise(await runNoise({ scenario: scenarioId, seed }));
    } catch (e) {
      setNoiseError(e.message);
      notify('ERROR', 'Noise comparison failed', e.message);
    } finally {
      setNoiseBusy(false);
    }
  };

  const cands = r ? Object.values(r.arbiter.candidates) : [];
  const b = r?.baseline.metrics;
  const o = r?.optimized.metrics;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<Cpu size={24} color="#2a2f36" />}
        title="QUBO OPTIMISATION ENGINE"
        subtitle="Signal timing as a 12-variable QUBO, solved with QAOA (Qiskit Aer simulator), simulated annealing and a greedy baseline."
        right={
          <Btn tone="ghost" onClick={() => setShowModal(true)}>
            <HelpCircle size={15} /> QUBO formulation
          </Btn>
        }
      />

      <OptimizationPipeline />

      {!r && <Note>Run the optimiser to see solver energies, runtimes and the simulated before/after comparison for this scenario.</Note>}

      {r && (
        <>
          <Panel title="SOLVER COMPARISON — SAME QUBO" icon={<Zap size={18} color="#1f6fd1" />}>
            <DataTable
              columns={[
                { key: 'solver', label: 'Solver', render: (c) => <strong>{c.solver_name.toUpperCase()}{c.solver_name === r.best_solver ? ' ★' : ''}</strong> },
                { key: 'energy', label: 'QUBO energy (lower = better)', render: (c) => fmt.n(c.qubo_energy, 3) },
                { key: 'rt', label: 'Runtime', render: (c) => `${fmt.n(c.runtime_seconds, 3)} s` },
                { key: 'feas', label: 'Feasible', render: (c) => (c.is_feasible ? 'yes' : 'no') },
                { key: 'plan', label: 'Plan', render: (c) => <code style={{ color: 'var(--text-2)' }}>{planText(c.signal_plan)}</code> },
              ]}
              rows={cands.map((c) => ({ id: c.solver_name, ...c }))}
            />
            <Note tone="ok">
              {r.verdict} QAOA: p={r.qaoa.p}, {r.qaoa.shots} shots, COBYLA maxiter {r.qaoa.maxiter}, backend {r.qaoa.backend}. No quantum advantage is claimed.
            </Note>
          </Panel>

          <Panel title="WHAT THE PLAN DOES IN THE SIMULATOR" icon={<Activity size={18} color="#1b7f3a" />}>
            <StatGrid>
              <Stat label="Avg wait (s/veh)" value={`${fmt.n(b.average_waiting_time)} → ${fmt.n(o.average_waiting_time)}`} sub="fixed 30 s → solver plan" />
              <Stat label="Person-delay" value={`${fmt.int(b.total_person_delay)} → ${fmt.int(o.total_person_delay)}`} />
              <Stat label="Throughput" value={`${fmt.int(b.throughput)} → ${fmt.int(o.throughput)}`} />
              <Stat label="Jain fairness" value={`${fmt.n(b.jain_fairness_index, 3)} → ${fmt.n(o.jain_fairness_index, 3)}`} />
              <Stat label="Max head wait (s)" value={`${fmt.n(b.max_approach_wait, 0)} → ${fmt.n(o.max_approach_wait, 0)}`} />
            </StatGrid>
            <Note tone="warn">{r.note} A lower QUBO energy does not guarantee a better simulated outcome, and the plan can make some metrics worse; both are shown as computed.</Note>
          </Panel>
        </>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <Panel title="QUBO TERMS" icon={<Layers size={18} color="#2a2f36" />}>
          {r ? (
            <StatGrid min={120}>
              {Object.entries(r.qubo.weights).map(([k, v]) => (
                <Stat key={k} label={k.replace(/_/g, ' ')} value={fmt.n(v, 1)} />
              ))}
            </StatGrid>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Weights appear after a run.</div>
          )}
          <div style={{ fontSize: '0.74rem', color: 'var(--muted)', lineHeight: 1.5 }}>
            Each junction picks exactly one green duration from {'{15, 30, 45}'} s (one-hot). The objective weighs queue waiting, capacity pressure, throughput and upstream/downstream coupling.
          </div>
        </Panel>

        <Panel title="IDEAL vs NOISY SIMULATION" icon={<Zap size={18} color="#b26a00" />}>
          {!canNoise ? (
            <Note>Needs a scenario with two ambulances (E, F or Belagavi-inspired two-ambulance): the circuit is the conflict QUBO.</Note>
          ) : (
            <>
              <Btn onClick={doNoise} disabled={noiseBusy}>{noiseBusy ? 'Sampling…' : 'Compare ideal vs noisy'}</Btn>
              {noiseError && <Note tone="error">{noiseError}</Note>}
              {noise && (
                <DataTable
                  columns={[
                    { key: 'b', label: 'Backend', render: (x) => x.backend_name },
                    { key: 'v', label: 'Valid orderings', render: (x) => `${fmt.n(x.valid_fraction * 100)}%` },
                    { key: 'o', label: 'Hit optimum', render: (x) => `${fmt.n(x.optimal_probability * 100)}%` },
                    { key: 't', label: 'Distance from ideal', render: (x) => fmt.n(x.tvd_vs_ideal, 3) },
                  ]}
                  rows={Object.values(noise.runs).map((x) => ({ id: x.kind, ...x }))}
                />
              )}
              <Note tone="warn">
                Simulation only, using a generic noise model. Real IBM hardware execution is optional future validation: the runtime path exists in the Python package but is unverified, and it is deliberately not reachable from this interface. {noise?.honesty_note}
              </Note>
            </>
          )}
        </Panel>
      </div>

      {showModal && <QuboExplanationModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
