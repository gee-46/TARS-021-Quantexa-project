import React from 'react';
import { X, Cpu, Layers, CheckCircle2, Sigma, ArrowRight } from 'lucide-react';

export default function QuboExplanationModal({ onClose }) {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      background: 'rgba(5, 3, 15, 0.8)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 12, 36, 0.98) 0%, rgba(8, 6, 20, 0.99) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.4)',
        borderRadius: '16px',
        padding: '28px',
        maxWidth: '720px',
        width: '100%',
        maxHeight: '85vh',
        overflowY: 'auto',
        boxShadow: '0 16px 48px rgba(0, 0, 0, 0.8), 0 0 32px rgba(82, 39, 255, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
      }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #5227FF, #A855F7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Sigma size={20} color="#fff" />
            </div>
            <div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fff' }}>
                WHAT IS BEING OPTIMIZED?
              </div>
              <div style={{ fontSize: '0.75rem', color: '#c4b5fd' }}>
                QUBO / Ising Mathematical Formulation & QAOA Objective Mapping
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: 'none',
              color: '#fff',
              borderRadius: '8px',
              padding: '6px',
              cursor: 'pointer',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Mathematical Formulation Card */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.4)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          borderRadius: '10px',
          padding: '16px',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
          color: '#00f5ff',
          lineHeight: 1.6,
        }}>
          <div style={{ color: '#a78bfa', fontWeight: 700, marginBottom: '6px' }}>
            Cost Hamiltonian (QUBO Objective):
          </div>
          <div>
            {"min H(x) = ∑ᵢ ( w_q · Qᵢ · xᵢ + w_d · Dᵢ · (1 - xᵢ) ) + ∑_<i,j> J_ij · xᵢ xⱼ + λ · ∑ₖ (∑ x_{i,phase} - 1)²"}
          </div>
        </div>

        {/* Variables and Inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.15)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
              Optimization Decision Variables
            </div>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.78rem', color: 'rgba(226, 232, 240, 0.85)', lineHeight: 1.6 }}>
              <li><strong>Signal Phase Binary Vector (x):</strong> 24 binary variables mapping green-light allocations across 6 hubs.</li>
              <li><strong>Queue Pressure (Q_i):</strong> Real-time vehicle counts waiting per intersection arm.</li>
              <li><strong>Road Capacity (C_e):</strong> Arterial throughput limit to prevent downstream gridlock.</li>
              <li><strong>Corridor Coordination (J_ij):</strong> Quadratic couplings penalizing out-of-sync adjacent signals.</li>
            </ul>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.15)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
              Multi-Objective Optimization Targets
            </div>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.78rem', color: 'rgba(226, 232, 240, 0.85)', lineHeight: 1.6 }}>
              <li><span style={{ color: '#10b981' }}>✓ Minimize aggregate waiting time</span> (-38%)</li>
              <li><span style={{ color: '#10b981' }}>✓ Minimize queue length</span> (-43.4%)</li>
              <li><span style={{ color: '#10b981' }}>✓ Maximize network throughput</span> (+36.8%)</li>
              <li><span style={{ color: '#10b981' }}>✓ Reduce fuel burn & CO₂</span> (-25%)</li>
              <li><span style={{ color: '#10b981' }}>✓ Preempt emergency ambulance paths</span> (-37.6% travel time)</li>
            </ul>
          </div>
        </div>

        {/* Quantum Workflow Flow */}
        <div style={{
          background: 'rgba(82, 39, 255, 0.12)',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.82rem',
          fontWeight: 700,
          color: '#fff',
        }}>
          <span>QUBO Formulation</span>
          <ArrowRight size={16} color="#a855f7" />
          <span>QAOA Circuit (p=3)</span>
          <ArrowRight size={16} color="#a855f7" />
          <span>Optimal Bitstring</span>
          <ArrowRight size={16} color="#a855f7" />
          <span style={{ color: '#10b981' }}>Synchronized Green Waves</span>
        </div>

        <button
          onClick={onClose}
          style={{
            padding: '12px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #5227FF, #A855F7)',
            border: 'none',
            color: '#fff',
            fontWeight: 700,
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
        >
          Close Technical Formulation
        </button>
      </div>
    </div>
  );
}
