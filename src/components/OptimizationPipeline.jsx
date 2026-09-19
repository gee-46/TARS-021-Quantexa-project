import React, { useState } from 'react';
import { useTraffic } from '../context/TrafficContext';
import { Cpu, Play, CheckCircle2, RotateCcw, Sparkles, ArrowRight, Activity, HelpCircle } from 'lucide-react';
import QuboExplanationModal from './QuboExplanationModal';

export default function OptimizationPipeline() {
  const {
    isOptimizing,
    optimizationResult,
    isOptimized,
    handleRunOptimization,
    handleApplyOptimization,
    handleResetSignals,
    network,
  } = useTraffic();

  const [showQuboModal, setShowQuboModal] = useState(false);

  const pipelineStages = [
    { label: 'TRAFFIC DATA', icon: '📡' },
    { label: 'NETWORK GRAPH', icon: '🕸️' },
    { label: 'QUBO', icon: '⚛️' },
    { label: 'QAOA', icon: '⚡' },
    { label: 'OPTIMIZED SIGNALS', icon: '🚦' },
    { label: 'SIMULATED RESULT', icon: '📉' },
  ];

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
      border: '1px solid rgba(139, 92, 246, 0.25)',
      borderRadius: '16px',
      padding: '22px',
      backdropFilter: 'blur(16px)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      display: 'flex',
      flexDirection: 'column',
      gap: '18px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={20} color="#a855f7" />
            <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff', letterSpacing: '0.02em' }}>
              QUANTUM OPTIMIZATION ENGINE
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#c4b5fd', marginTop: '3px' }}>
            Backend: <strong>Qiskit Aer local simulator (QAOA p={optimizationResult?.qaoa?.p ?? 1}) + SA + Greedy</strong>
          </div>
        </div>

        <button
          onClick={() => setShowQuboModal(true)}
          style={{
            background: 'rgba(82, 39, 255, 0.2)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            color: '#c4b5fd',
            borderRadius: '6px',
            padding: '5px 10px',
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(82, 39, 255, 0.4)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(82, 39, 255, 0.2)')}
        >
          <HelpCircle size={13} />
          What is being optimized?
        </button>
      </div>

      {/* Parameter Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '8px',
      }}>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.62rem', color: 'rgba(196, 181, 253, 0.7)', textTransform: 'uppercase' }}>Method</div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#00f5ff', marginTop: '2px' }}>QAOA · SA · Greedy</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.62rem', color: 'rgba(196, 181, 253, 0.7)', textTransform: 'uppercase' }}>Formulation</div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a855f7', marginTop: '2px' }}>QUBO / Ising</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.62rem', color: 'rgba(196, 181, 253, 0.7)', textTransform: 'uppercase' }}>Variables</div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff', marginTop: '2px' }}>{optimizationResult?.qubo?.variables ?? 12} binary</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.62rem', color: 'rgba(196, 181, 253, 0.7)', textTransform: 'uppercase' }}>Constraints</div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f59e0b', marginTop: '2px' }}>One-hot per junction</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.62rem', color: 'rgba(196, 181, 253, 0.7)', textTransform: 'uppercase' }}>Objective</div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>Signal Timing</div>
        </div>
      </div>

      {/* Visual Pipeline Flow */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.4)',
        border: '1px solid rgba(139, 92, 246, 0.15)',
        borderRadius: '10px',
        padding: '14px 10px',
      }}>
        <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: '10px' }}>
          Hybrid Optimization Pipeline Architecture
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '4px',
        }}>
          {pipelineStages.map((stage, idx) => (
            <React.Fragment key={stage.label}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                flex: 1,
                background: isOptimizing && idx === 3
                  ? 'rgba(168, 85, 247, 0.3)'
                  : isOptimized
                  ? 'rgba(16, 185, 129, 0.12)'
                  : 'rgba(255, 255, 255, 0.04)',
                border: isOptimizing && idx === 3
                  ? '1px solid #a855f7'
                  : isOptimized
                  ? '1px solid rgba(16, 185, 129, 0.3)'
                  : '1px solid rgba(255, 255, 255, 0.08)',
                padding: '8px 4px',
                borderRadius: '6px',
                textAlign: 'center',
              }}>
                <span style={{ fontSize: '1.1rem' }}>{stage.icon}</span>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#f8fafc' }}>{stage.label}</span>
              </div>
              {idx < pipelineStages.length - 1 && (
                <ArrowRight size={14} color="rgba(139, 92, 246, 0.5)" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Live Stage Execution List */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.3)',
        borderRadius: '8px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        fontSize: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOptimized || optimizationResult ? '#10b981' : 'rgba(216, 207, 247, 0.7)' }}>
          <CheckCircle2 size={14} color={isOptimized || optimizationResult ? '#10b981' : 'rgba(139, 92, 246, 0.4)'} />
          <span>Traffic state collected ({network?.nodes?.length ?? '—'} junctions, {network?.edges?.length ?? '—'} arterial links)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOptimized || optimizationResult ? '#10b981' : 'rgba(216, 207, 247, 0.7)' }}>
          <CheckCircle2 size={14} color={isOptimized || optimizationResult ? '#10b981' : 'rgba(139, 92, 246, 0.4)'} />
          <span>Upstream/downstream couplings encoded in the QUBO</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOptimized || optimizationResult ? '#10b981' : 'rgba(216, 207, 247, 0.7)' }}>
          <CheckCircle2 size={14} color={isOptimized || optimizationResult ? '#10b981' : 'rgba(139, 92, 246, 0.4)'} />
          <span>QUBO formulated ({optimizationResult?.qubo?.variables ?? 12} binary variables: 4 junctions × 3 green durations)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOptimizing ? '#00f5ff' : isOptimized || optimizationResult ? '#10b981' : 'rgba(216, 207, 247, 0.7)' }}>
          <CheckCircle2 size={14} color={isOptimized || optimizationResult ? '#10b981' : 'rgba(139, 92, 246, 0.4)'} />
          <span>{isOptimizing ? '⟳ Running QAOA on Qiskit Aer, plus SA and Greedy...' : optimizationResult ? `Solved: best solver ${optimizationResult.best_solver.toUpperCase()}` : 'Waiting to solve'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOptimized || optimizationResult ? '#10b981' : 'rgba(216, 207, 247, 0.7)' }}>
          <CheckCircle2 size={14} color={isOptimized || optimizationResult ? '#10b981' : 'rgba(139, 92, 246, 0.4)'} />
          <span>{optimizationResult ? `Signal plan ${Object.entries(optimizationResult.best_plan).map(([k, v]) => `${k}:${v}s`).join(' ')} (QUBO energy ${optimizationResult.best_energy.toFixed(2)})` : 'Signal plan not generated yet'}</span>
        </div>
      </div>

      {optimizationResult && (
        <div style={{ fontSize: '0.74rem', color: 'rgba(226, 232, 240, 0.9)', background: 'rgba(82, 39, 255, 0.1)', border: '1px solid rgba(139, 92, 246, 0.25)', borderRadius: '8px', padding: '8px 12px' }}>
          {optimizationResult.verdict}
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <button
          onClick={handleRunOptimization}
          disabled={isOptimizing}
          style={{
            flex: 1.4,
            padding: '12px 18px',
            borderRadius: '8px',
            background: isOptimizing
              ? 'rgba(82, 39, 255, 0.3)'
              : 'linear-gradient(135deg, #5227FF 0%, #A855F7 100%)',
            border: 'none',
            color: '#fff',
            fontWeight: 700,
            fontSize: '0.85rem',
            cursor: isOptimizing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            boxShadow: isOptimizing ? 'none' : '0 0 20px rgba(168, 85, 247, 0.4)',
            transition: 'all 0.2s',
          }}
        >
          {isOptimizing ? (
            <>
              <Activity size={16} className="spin" />
              <span>Solving (QAOA on Aer)...</span>
            </>
          ) : (
            <>
              <Play size={16} />
              <span>RUN QUANTUM OPTIMIZATION</span>
            </>
          )}
        </button>

        <button
          onClick={handleApplyOptimization}
          disabled={!optimizationResult || isOptimized}
          style={{
            flex: 1.1,
            padding: '12px 16px',
            borderRadius: '8px',
            background: optimizationResult && !isOptimized
              ? 'rgba(16, 185, 129, 0.25)'
              : 'rgba(255, 255, 255, 0.05)',
            border: optimizationResult && !isOptimized
              ? '1px solid #10b981'
              : '1px solid rgba(255, 255, 255, 0.1)',
            color: optimizationResult && !isOptimized ? '#6ee7b7' : 'rgba(255, 255, 255, 0.4)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: optimizationResult && !isOptimized ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}
        >
          <CheckCircle2 size={16} />
          <span>APPLY OPTIMIZED SIGNALS</span>
        </button>

        <button
          onClick={handleResetSignals}
          style={{
            padding: '12px 14px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}
          title="Reset to Classical Fixed Timing"
        >
          <RotateCcw size={15} />
          <span>RESET</span>
        </button>
      </div>

      {showQuboModal && <QuboExplanationModal onClose={() => setShowQuboModal(false)} />}
    </div>
  );
}
