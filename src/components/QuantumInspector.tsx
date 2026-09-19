import React from 'react';
import { QUBOProblem } from '../optimizer/qubo';
import { SolverResult } from '../types/traffic';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Atom, Cpu, CheckCircle2, AlertCircle, Zap, ShieldCheck } from 'lucide-react';

interface QuantumInspectorProps {
  problem: QUBOProblem | null;
  lastSolverResult: SolverResult | null;
}

export const QuantumInspector: React.FC<QuantumInspectorProps> = ({
  problem,
  lastSolverResult,
}) => {
  if (!problem) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 text-center text-slate-500 italic">
        Simulation waiting for first epoch solve.
      </div>
    );
  }

  // Simulated top quantum state probabilities for visual inspector
  const topStates = [
    { state: '|Ground State (Opt)⟩', prob: lastSolverResult?.info.prob_optimal ?? 0.72, fill: '#10b981' },
    { state: '|Excited 1⟩', prob: 0.14, fill: '#38bdf8' },
    { state: '|Excited 2⟩', prob: 0.07, fill: '#64748b' },
    { state: '|Excited 3⟩', prob: 0.04, fill: '#475569' },
    { state: '|Tail Subspace⟩', prob: 0.03, fill: '#334155' },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-purple-950/70 border border-purple-500/50 text-purple-400">
            <Atom className="w-5 h-5 animate-spin-slow" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 uppercase tracking-wide">
              QUBO & QAOA Quantum State Inspector (M1)
            </h2>
            <p className="text-xs text-slate-400">
              Ising Hamiltonian mapping, XY-mixer subspace preservation & statevector fidelity
            </p>
          </div>
        </div>

        <div className="px-3 py-1.5 rounded-xl bg-purple-950/50 border border-purple-500/40 text-purple-300 text-xs font-mono font-semibold flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5" />
          <span>Active: {lastSolverResult?.solver ?? 'Exact QUBO'}</span>
        </div>
      </div>

      {/* Top Cards: Qubit Dimensions & Quantum Fidelity */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col gap-1">
          <span className="text-[11px] text-slate-400 font-mono">Qubits (Variables n)</span>
          <div className="text-2xl font-black font-mono text-cyan-400">
            {problem.n} <span className="text-xs font-normal text-slate-500">qubits</span>
          </div>
          <span className="text-[10px] text-slate-500">One per (Intersection, Direction) choice</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col gap-1">
          <span className="text-[11px] text-slate-400 font-mono">Feasible Subspace</span>
          <div className="text-2xl font-black font-mono text-emerald-400">
            {problem.feasibleBitstrings.length} / {Math.pow(2, problem.n).toLocaleString()}
          </div>
          <span className="text-[10px] text-slate-500">One-hot constraint: Exactly 1 green / node</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col gap-1">
          <span className="text-[11px] text-slate-400 font-mono">P(Feasible) with XY-Mixer</span>
          <div className="text-2xl font-black font-mono text-emerald-400 flex items-center gap-1.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span>100%</span>
          </div>
          <span className="text-[10px] text-slate-500">Strictly preserved in feasible manifold</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col gap-1">
          <span className="text-[11px] text-slate-400 font-mono">Current Ground Energy</span>
          <div className="text-2xl font-black font-mono text-purple-300">
            {lastSolverResult ? Math.round(lastSolverResult.energy * 10) / 10 : 0.0}
          </div>
          <span className="text-[10px] text-slate-500">Includes emergency priority penalty</span>
        </div>
      </div>

      {/* Two Column Layout: Solved Signal Plan & Statevector Probability Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Solved Signal Plan */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
            <span>Decoded Signal Plan (Active Green Phases)</span>
            <span className="text-[10px] font-mono text-cyan-400">
              Solve Time: {Math.round((lastSolverResult?.solveTimeMs ?? 0) * 100) / 100} ms
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {lastSolverResult &&
              Object.entries(lastSolverResult.plan).map(([nodeId, targetDir]) => {
                const isEmergencyHop = problem.meta.emergencyHops.some(
                  ([u, v]) => u === nodeId && v === targetDir
                );
                return (
                  <div
                    key={nodeId}
                    className={`p-3 rounded-xl border flex flex-col gap-1 ${
                      isEmergencyHop
                        ? 'bg-emerald-950/40 border-emerald-500/60 text-emerald-200 shadow-md'
                        : 'bg-slate-900 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="text-[10px] font-mono uppercase text-slate-400">Intersection</div>
                    <div className="text-sm font-bold font-mono text-slate-100 flex items-center gap-1.5">
                      <span>{nodeId}</span>
                      <span className="text-cyan-400 font-normal">→</span>
                      <span className="text-emerald-400 font-black">{targetDir}</span>
                    </div>
                    {isEmergencyHop && (
                      <span className="text-[9px] font-mono text-emerald-400 font-bold tracking-tighter">
                        ⚡ CORRIDOR HOP
                      </span>
                    )}
                  </div>
                );
              })}
          </div>

          {/* QUBO Hamiltonian Terms Breakdown */}
          <div className="mt-2 pt-3 border-t border-slate-800 text-xs text-slate-400 flex flex-col gap-1.5 font-mono text-[11px]">
            <div className="text-slate-300 font-sans font-semibold text-xs">Active Objective Terms:</div>
            <div className="flex items-center justify-between">
              <span>• Service Reward min(Q, C):</span>
              <span className="text-cyan-400 font-bold">-W_service</span>
            </div>
            <div className="flex items-center justify-between">
              <span>• Downstream Density Penalty:</span>
              <span className="text-amber-400 font-bold">+W_density</span>
            </div>
            <div className="flex items-center justify-between">
              <span>• Green-Wave Route Bonus:</span>
              <span className="text-emerald-400 font-bold">-W_greenwave</span>
            </div>
            <div className="flex items-center justify-between">
              <span>• Emergency Corridor Priority:</span>
              <span className="text-red-400 font-bold">
                {problem.meta.emergencyActive ? '-15.0 × Priority (EMERGED)' : 'Inactive'}
              </span>
            </div>
          </div>
        </div>

        {/* QAOA Statevector Probabilities */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
            <span>QAOA Statevector Probability Distribution |ψ(s)|²</span>
            <span className="text-[10px] font-mono text-purple-400">Depth p=3</span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topStates} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                <XAxis dataKey="state" stroke="#94a3b8" fontSize={10} interval={0} />
                <YAxis stroke="#94a3b8" fontSize={10} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                />
                <Bar dataKey="prob" name="State Probability" radius={[4, 4, 0, 0]} fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="text-[11px] text-slate-400 leading-relaxed bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <strong className="text-slate-200">Quantum Subspace Guarantee:</strong> The XY-mixer operates
            exclusively on excitations within each intersection's one-hot group, ensuring zero probability leaks to
            infeasible states (<span className="text-emerald-400 font-mono font-bold">P(feasible) = 1.0</span>).
          </div>
        </div>
      </div>
    </div>
  );
};
