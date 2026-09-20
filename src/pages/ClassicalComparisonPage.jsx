import React from 'react';
import { GitCompare, Cpu } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { PageHeader, Panel, DataTable, Note, Btn, fmt } from '../components/ui';
import PlotlyChart from '../components/PlotlyChart';

const COLOR = { qaoa: '#a855f7', sa: '#00f5ff', greedy: '#f59e0b' };
const planText = (p) => Object.entries(p || {}).map(([k, v]) => `${k}:${v}s`).join('  ');

export default function ClassicalComparisonPage() {
  const { optimizationResult: r, isOptimizing, handleRunOptimization } = useTraffic();
  const cands = r ? Object.values(r.arbiter.candidates) : [];
  const b = r?.baseline.metrics;
  const o = r?.optimized.metrics;
  const row = (label, key, d, lowerBetter) => ({
    id: key,
    label,
    base: fmt.n(b[key], d),
    opt: fmt.n(o[key], d),
    diff: b[key] === o[key] ? 'same' : (lowerBetter ? o[key] < b[key] : o[key] > b[key]) ? 'better' : 'worse',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<GitCompare size={24} color="#a855f7" />}
        title="SOLVER COMPARISON"
        subtitle="QAOA (Aer simulator) vs simulated annealing vs greedy on the identical QUBO — reported as computed, including when QAOA does not win."
        right={<Btn onClick={handleRunOptimization} disabled={isOptimizing}><Cpu size={15} />{isOptimizing ? 'Solving…' : 'Run comparison'}</Btn>}
      />

      {!r && <Note>Run the comparison to solve this scenario's QUBO with all three solvers.</Note>}

      {r && (
        <>
          <Panel title="QUBO ENERGY BY SOLVER (lower is better)">
            <PlotlyChart
              height={220}
              data={[
                {
                  type: 'bar',
                  orientation: 'h',
                  x: cands.map((c) => c.qubo_energy),
                  y: cands.map((c) => c.solver_name.toUpperCase()),
                  marker: { color: cands.map((c) => COLOR[c.solver_name] || '#94a3b8') },
                  text: cands.map((c) => c.qubo_energy.toFixed(2)),
                  textposition: 'auto',
                  hovertemplate: '%{y}: energy %{x:.3f}<extra></extra>',
                },
              ]}
              layout={{ xaxis: { title: { text: 'QUBO energy (lower is better)' } }, margin: { l: 80, r: 16, t: 10, b: 46 } }}
            />
            <DataTable
              columns={[
                { key: 's', label: 'Solver', render: (c) => <strong>{c.solver_name.toUpperCase()}{c.solver_name === r.best_solver ? ' ★' : ''}</strong> },
                { key: 'e', label: 'Energy', render: (c) => fmt.n(c.qubo_energy, 3) },
                { key: 't', label: 'Runtime', render: (c) => `${fmt.n(c.runtime_seconds, 4)} s` },
                { key: 'f', label: 'Feasible', render: (c) => (c.is_feasible ? 'yes' : 'no') },
                { key: 'p', label: 'Plan', render: (c) => <code style={{ color: '#c4b5fd' }}>{planText(c.signal_plan)}</code> },
              ]}
              rows={cands.map((c) => ({ id: c.solver_name, ...c }))}
            />
            <Note tone="ok">{r.verdict}</Note>
          </Panel>

          <Panel title="SIMULATED OUTCOME: FIXED 30 s PLAN vs SOLVER PLAN">
            <DataTable
              columns={[
                { key: 'label', label: 'Metric' },
                { key: 'base', label: 'Fixed 30 s' },
                { key: 'opt', label: `Solver plan (${r.best_solver.toUpperCase()})` },
                { key: 'diff', label: 'Result', render: (x) => <span style={{ color: x.diff === 'better' ? '#10b981' : x.diff === 'worse' ? '#ef4444' : '#94a3b8', fontWeight: 700 }}>{x.diff}</span> },
              ]}
              rows={[
                row('Average wait (s / vehicle)', 'average_waiting_time', 1, true),
                row('Person-delay (person-s)', 'total_person_delay', 0, true),
                row('Throughput (vehicles)', 'throughput', 0, false),
                row('Jain fairness', 'jain_fairness_index', 3, false),
                row('Max approach wait (s)', 'max_approach_wait', 0, true),
                row('Idling CO₂ (kg, model)', 'estimated_co2_kg', 2, true),
              ]}
            />
          </Panel>
        </>
      )}

      <Note tone="warn">
        What this does and does not show: at 12 variables an exhaustive search is instant and classical heuristics find the optimum reliably, so QAOA here is a
        demonstration on a classical simulator, not a speedup. No quantum advantage is claimed. Results are for one seed on an assumed-traffic simulator.
      </Note>
    </div>
  );
}
