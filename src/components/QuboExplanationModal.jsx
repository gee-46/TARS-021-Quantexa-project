import React from 'react';
import { X } from 'lucide-react';

const h = { fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-2)', letterSpacing: '0.06em', textTransform: 'uppercase', margin: '16px 0 4px' };
const p = { fontSize: '0.84rem', lineHeight: 1.6, color: 'var(--text)', margin: 0 };

export default function QuboExplanationModal({ onClose }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(28,34,41,0.55)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }} onClick={onClose}>
      <div role="dialog" aria-label="What is being optimised" style={{ width: 'min(720px, 100%)', maxHeight: '86vh', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius)', padding: '18px 22px', boxShadow: '0 12px 40px rgba(0,0,0,0.3)' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.05rem' }}>What is being optimised?</h2>
          <button onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={20} /></button>
        </div>

        <div style={h}>Decision variables</div>
        <p style={p}>Each of the 4 junctions chooses exactly one green duration from 15 s, 30 s or 45 s inside a 60 s cycle: 4 × 3 = <strong>12 binary variables</strong>, so the QAOA circuit has <strong>12 qubits</strong>.</p>

        <div style={h}>Objective (QUBO)</div>
        <p style={{ ...p, fontFamily: 'var(--mono)', background: 'var(--surface-2)', border: '1px solid var(--border)', padding: '8px 10px', borderRadius: 4 }}>E(x) = xᵀ Q x + c = waiting + capacity pressure − throughput + coupling + λ·(one-hot violations)</p>
        <p style={{ ...p, marginTop: 6 }}>The one-hot penalty forces one duration per junction. Waiting, capacity pressure, throughput and upstream/downstream coupling terms are weighted by the values shown on the optimisation page. The QUBO is converted to an Ising Hamiltonian for QAOA.</p>

        <div style={h}>Solvers</div>
        <p style={p}>The same QUBO goes to QAOA (Qiskit Aer, a classical simulator), simulated annealing, and a greedy local search. The interface reports which one reached the lowest energy on that instance, including when QAOA loses or ties. At 12 variables exhaustive search is instant, so no quantum advantage is claimed.</p>

        <div style={h}>People-weighted and fair</div>
        <p style={p}>The simulator counts person-delay (cars carry their occupancy, buses ~30–40 people) and reports the Jain fairness index and starvation violations, so a plan that favours one road at the expense of another is visible.</p>

        <div style={h}>Emergency vehicles</div>
        <p style={p}>When two ambulances need the same junction, a separate small conflict QUBO (K² variables for K vehicles) sequences them by priority-weighted waiting time. Preemption forces the whole junction green; turn phases are not modelled.</p>

        <div style={h}>Scope</div>
        <p style={p}>Everything shown is simulated: traffic volumes are assumed, not measured, and results are not validated against real traffic.</p>
      </div>
    </div>
  );
}
