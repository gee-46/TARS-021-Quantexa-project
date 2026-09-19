import React from 'react';
import { Layers, Cpu, Server, Network, BarChart3, Database, ArrowDown, Sparkles } from 'lucide-react';

export default function ArchitecturePage() {
  const pipelineSteps = [
    {
      title: '1. Traffic Sensors & Telemetry (IoT / SUMO)',
      layer: 'SIMULATION & SENSING',
      color: '#38bdf8',
      desc: 'Real-time induction loop sensors, camera feeds, and SUMO vehicle trajectory tracking ingest speed, queue lengths, and density per arm.',
      tech: 'SUMO / OpenStreetMap / IoT MQTT Streams',
    },
    {
      title: '2. Network Topology Graph Construction',
      layer: 'CLASSICAL COMPONENT',
      color: '#a78bfa',
      desc: 'Builds directed graph adjacency matrices and bottleneck capacities across all connected urban intersections.',
      tech: 'NetworkX Graph Data Model (Python / JS)',
    },
    {
      title: '3. Classical Preprocessing & Constraint Normalization',
      layer: 'CLASSICAL COMPONENT',
      color: '#a78bfa',
      desc: 'Filters incoming demand, calculates phase switching penalties, and bounds road saturation thresholds.',
      tech: 'NumPy / Classical Controller Filters',
    },
    {
      title: '4. Combinatorial QUBO / Ising Hamiltonian Formulation',
      layer: 'QUANTUM COMPONENT',
      color: '#a855f7',
      desc: 'Encodes 24 binary signal timing decisions into quadratic cost matrix H(x) with Lagrange multipliers (λ) enforcing safety constraints.',
      tech: 'QUBO Cost Formulation (PyQUBO / Qiskit Optimization)',
    },
    {
      title: '5. Quantum Approximate Optimization Algorithm (QAOA)',
      layer: 'QUANTUM COMPONENT',
      color: '#a855f7',
      desc: 'Executes p=3 parameterized quantum circuit ansatz with alternating Cost and Mixer unitary gates, optimized via classical COBYLA loop.',
      tech: 'Qiskit / Qiskit Aer Statevector (IBM Quantum / Braket QPU ready)',
    },
    {
      title: '6. Optimal Signal Configuration Extraction',
      layer: 'CLASSICAL COMPONENT',
      color: '#a78bfa',
      desc: 'Samples optimal bitstring corresponding to the minimum-energy ground state to produce synchronized green wave schedules.',
      tech: 'Bitstring Decoder & Phase Actuation Engine',
    },
    {
      title: '7. Traffic Simulation Actuation & Corridor Control',
      layer: 'SIMULATION & CONTROL',
      color: '#38bdf8',
      desc: 'Updates physical traffic lights across all 6 hubs, clears congestion waves, and coordinates emergency green corridors.',
      tech: 'SUMO TraCI / Smart Traffic Actuators',
    },
    {
      title: '8. Real-Time Command Visualization & Analytics',
      layer: 'FRONTEND COMPONENT',
      color: '#00f5ff',
      desc: 'Ultra-low-latency command center with WebGL procedural shaders, interactive network visualizer, and dynamic variable typography.',
      tech: 'React 19 / Vite / OGL WebGL / Roboto Flex / React Bits',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers size={24} color="#00f5ff" />
          SYSTEM ARCHITECTURE & HYBRID DATA FLOW
        </h1>
        <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>
          End-to-End Technical Stack: From IoT Traffic Ingestion to QUBO Mapping, QAOA Simulation, and Command Center Actuation
        </p>
      </div>

      {/* Layer Color Legend */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        background: 'rgba(16, 12, 34, 0.95)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '12px',
        padding: '14px 20px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: 700 }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#38bdf8' }} />
          <span style={{ color: '#38bdf8' }}>SIMULATION & SENSING LAYER</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: 700 }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#a78bfa' }} />
          <span style={{ color: '#a78bfa' }}>CLASSICAL PROCESSING LAYER</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: 700 }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#a855f7' }} />
          <span style={{ color: '#a855f7' }}>QUANTUM OPTIMIZATION LAYER</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: 700 }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#00f5ff' }} />
          <span style={{ color: '#00f5ff' }}>FRONTEND COMMAND LAYER</span>
        </div>
      </div>

      {/* Vertical Data Flow Pipeline */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {pipelineSteps.map((step, idx) => (
          <React.Fragment key={step.title}>
            <div style={{
              background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
              border: `1px solid ${step.color}40`,
              borderRadius: '12px',
              padding: '18px',
              backdropFilter: 'blur(12px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1 }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '8px',
                  background: `${step.color}20`,
                  border: `1px solid ${step.color}60`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  color: step.color,
                  fontSize: '0.95rem',
                }}>
                  0{idx + 1}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff' }}>
                      {step.title}
                    </span>
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      color: step.color,
                      background: `${step.color}15`,
                      border: `1px solid ${step.color}40`,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}>
                      {step.layer}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.78rem', color: 'rgba(216, 207, 247, 0.8)', marginTop: '4px', lineHeight: 1.4 }}>
                    {step.desc}
                  </div>
                </div>
              </div>

              <div style={{
                fontSize: '0.72rem',
                fontFamily: 'monospace',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(139, 92, 246, 0.15)',
                padding: '6px 12px',
                borderRadius: '6px',
                color: '#c4b5fd',
                whiteSpace: 'nowrap',
              }}>
                {step.tech}
              </div>
            </div>

            {idx < pipelineSteps.length - 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '2px 0' }}>
                <ArrowDown size={18} color="rgba(168, 85, 247, 0.6)" />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
