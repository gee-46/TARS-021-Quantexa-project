import React from 'react';
import { X, Sigma } from 'lucide-react';

const overlay = { position: 'fixed', inset: 0, background: 'rgba(3, 2, 10, 0.82)', backdropFilter: 'blur(12px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' };
const box = { width: 'min(760px, 100%)', maxHeight: '88vh', overflowY: 'auto', background: 'linear-gradient(135deg, rgba(18, 14, 40, 0.98), rgba(8, 6, 20, 0.99))', border: '1px solid rgba(139, 92, 246, 0.35)', borderRadius: '16px', padding: '24px', boxShadow: '0 16px 48px rgba(0,0,0,.8)', color: '#e2e8f0' };
const h = { fontSize: '0.85rem', fontWeight: 800, color: '#c4b5fd', margin: '18px 0 6px' };
const p = { fontSize: '0.82rem', lineHeight: 1.6, color: 'rgba(226, 232, 240, 0.9)', margin: 0 };
const code = { background: 'rgba(0,0,0,.45)', border: '1px solid rgba(139,92,246,.2)', borderRadius: '8px', padding: '10px 12px', fontFamily: 'monospace', fontSize: '0.78rem', color: '#7dd3fc', margin: '6px 0' };

export default function QuboExplanationModal({ onClose }) {
  return (
    <div style={overlay} onClick={onClose}>
      <div style={box} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>
            <Sigma size={20} color="#a855f7" /> What is being optimised?
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#c4b5fd', cursor: 'pointer' }} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div style={h}>Decision variables</div>
        <p style={p}>
          Each of the 4 junctions chooses exactly one green duration from 15 s, 30 s or 45 s inside a 60 s cycle:
          4 × 3 = <strong>12 binary variables</strong>, so the QAOA circuit has <strong>12 qubits</strong>.
        </p>

        <div style={h}>Objective (QUBO)</div>
        <div style={code}>E(x) = xᵀ Q x + c = waiting + capacity pressure − throughput + coupling + λ·(one-hot violations)</div>
        <p style={p}>
          The one-hot penalty forces one duration per junction. Waiting, capacity pressure, throughput and upstream/downstream coupling terms are weighted by
          the values shown on the optimiser page. The QUBO is converted to an Ising Hamiltonian for QAOA.
        </p>

        <div style={h}>Solvers</div>
        <p style={p}>
          The same QUBO goes to QAOA (Qiskit Aer, a classical simulator), simulated annealing, and a greedy local search. The interface reports which one
          reached the lowest energy on that instance — including when QAOA loses or ties. At 12 variables exhaustive search is instant, so no quantum
          advantage is claimed.
        </p>

        <div style={h}>People-weighted and fair</div>
        <p style={p}>
          The simulator counts person-delay (cars carry their occupancy, buses ~30–40 people) and reports the Jain fairness index and starvation
          violations, so a plan that favours one road at the expense of another is visible.
        </p>

        <div style={h}>Emergency vehicles</div>
        <p style={p}>
          When two ambulances need the same junction, a separate small conflict QUBO (K² variables for K vehicles) sequences them by priority-weighted
          waiting time. Preemption forces the whole junction green; turn phases are not modelled.
        </p>

        <div style={h}>Scope</div>
        <p style={p}>
          Everything shown is simulated: traffic volumes are assumed, not measured, and results are not validated against real traffic.
        </p>
      </div>
    </div>
  );
}
