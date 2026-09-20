import React from 'react';
import { Layers, ArrowDown } from 'lucide-react';
import { PageHeader, Panel, Note } from '../components/ui';

// Describes what is actually implemented in this repository (module names are real files).
const STAGES = [
  { t: '1. Scenario', d: 'Demand, queues, buses, cross-street traffic and ambulances for a 4-junction arterial (I1 → I4). Assumed values, not sensor data.', m: 'simulation/scenario.py, simulation/registry.py' },
  { t: '2. Microscopic simulator', d: 'Second-by-second queues, Poisson arrivals, cyclic signals, person-delay, Jain fairness and idling CO₂.', m: 'simulation/engine.py' },
  { t: '3. QUBO builder', d: '12 binary variables (4 junctions × {15, 30, 45} s). Waiting, capacity, throughput, coupling and one-hot terms.', m: 'optimization/qubo_builder.py' },
  { t: '4. Ising mapping + QAOA', d: 'QUBO → Ising Hamiltonian → parameterised QAOA circuit run on Qiskit Aer (a local classical simulator) with COBYLA.', m: 'optimization/ising_converter.py, production_qaoa.py' },
  { t: '5. Solver arbiter', d: 'QAOA, simulated annealing and greedy solve the same QUBO; the lowest energy wins, and losses/ties are reported.', m: 'optimization/solver_arbiter.py' },
  { t: '6. Adaptive loop', d: 'The plan is re-solved every N seconds from the current queues (rolling horizon).', m: 'simulation/adaptive_controller.py' },
  { t: '7. Emergency corridor + conflict QUBO', d: 'Ambulances preempt whole junctions; conflicting ambulances are sequenced by a K²-variable QUBO.', m: 'simulation/emergency_controller.py, optimization/emergency_conflict.py' },
  { t: '8. Pareto sweep', d: 'Emergency priority λ (preemption duty) vs civilian person-delay, split into arterial and cross-street parts.', m: 'optimization/pareto.py' },
  { t: '9. HTTP API', d: 'FastAPI service that returns exactly what the modules above compute; this interface is a client of it.', m: 'api_server.py' },
];

export default function ArchitecturePage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader icon={<Layers size={24} color="#1f6fd1" />} title="SYSTEM ARCHITECTURE" subtitle="What is implemented, module by module." />
      <Panel>
        {STAGES.map((s, i) => (
          <React.Fragment key={s.t}>
            <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 14px' }}>
              <div style={{ fontWeight: 800, color: '#fff', fontSize: '0.9rem' }}>{s.t}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text)', margin: '4px 0', lineHeight: 1.5 }}>{s.d}</div>
              <code style={{ fontSize: '0.7rem', color: '#7dd3fc' }}>{s.m}</code>
            </div>
            {i < STAGES.length - 1 && <ArrowDown size={16} color="#8b949e" style={{ alignSelf: 'center' }} />}
          </React.Fragment>
        ))}
      </Panel>
      <Panel title="NOT IMPLEMENTED / NOT CLAIMED">
        <Note tone="warn">
          There are no live sensors, SUMO/TraCI link, or real signal actuation. QAOA runs on a classical simulator; real IBM hardware execution is optional future
          validation (the runtime path exists in the Python package, is unverified, and is not reachable from this interface). Turn phases are not modelled, preemption
          forces a whole junction green, and no quantum advantage is claimed.
        </Note>
      </Panel>
    </div>
  );
}
