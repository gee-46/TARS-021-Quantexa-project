import React from 'react';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import IntersectionDetailModal from '../components/IntersectionDetailModal';
import { useTraffic } from '../context/TrafficContext';
import { Network, CheckCircle2, RotateCcw, Cpu, Play } from 'lucide-react';

export default function TrafficNetworkPage() {
  const {
    intersections,
    isOptimized,
    isOptimizing,
    optimizationResult,
    handleRunOptimization,
    handleApplyOptimization,
    handleResetSignals,
    selectedIntersectionId,
    setSelectedIntersectionId,
  } = useTraffic();

  const getSignalBadge = (sig) => {
    let color = '#ef4444';
    if (sig === 'GREEN') color = '#10b981';
    if (sig === 'YELLOW') color = '#f59e0b';
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 8px',
        borderRadius: '4px',
        background: `${color}20`,
        border: `1px solid ${color}60`,
        color: color,
        fontWeight: 700,
        fontSize: '0.75rem',
      }}>
        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: color }} />
        {sig}
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Network size={24} color="#00f5ff" />
            TRAFFIC NETWORK & ADAPTIVE SIGNAL CONTROL
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>
            Four-junction arterial (I1 → I4): simulated queues, waits and the signal plan in use
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleRunOptimization}
            disabled={isOptimizing}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #5227FF, #A855F7)',
              border: 'none',
              color: '#fff',
              fontWeight: 700,
              fontSize: '0.8rem',
              cursor: isOptimizing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Cpu size={15} />
            <span>RUN QUBO OPTIMISER</span>
          </button>

          <button
            onClick={handleApplyOptimization}
            disabled={!optimizationResult || isOptimized}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              background: optimizationResult && !isOptimized ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: optimizationResult && !isOptimized ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
              color: optimizationResult && !isOptimized ? '#6ee7b7' : 'rgba(255, 255, 255, 0.4)',
              fontWeight: 700,
              fontSize: '0.8rem',
              cursor: optimizationResult && !isOptimized ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <CheckCircle2 size={15} />
            <span>APPLY OPTIMIZED SIGNALS</span>
          </button>

          <button
            onClick={handleResetSignals}
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              fontWeight: 600,
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <RotateCcw size={15} />
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* Main Network Graph & Node Inspector */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.7fr 1fr',
        gap: '20px',
      }}>
        <TrafficNetworkVisualizer />
        <IntersectionDetailModal />
      </div>

      {/* Adaptive Signal Control Table */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '16px',
        padding: '20px',
        backdropFilter: 'blur(16px)',
      }}>
        <div style={{
          fontSize: '0.95rem',
          fontWeight: 800,
          color: '#fff',
          letterSpacing: '0.02em',
          marginBottom: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span>ADAPTIVE SIGNAL CONTROL TABLE</span>
          <span style={{ fontSize: '0.72rem', color: '#a78bfa', fontWeight: 600 }}>
            {isOptimized ? '● Solver-chosen plan applied (simulated)' : '● Fixed 30 s plan active'}
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: '0.82rem',
          }}>
            <thead>
              <tr style={{
                borderBottom: '1px solid rgba(139, 92, 246, 0.2)',
                color: 'rgba(196, 181, 253, 0.8)',
                fontSize: '0.72rem',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>
                <th style={{ padding: '10px 12px' }}>Intersection</th>
                <th style={{ padding: '10px 12px' }}>Current Signal</th>
                <th style={{ padding: '10px 12px' }}>Solver Plan</th>
                <th style={{ padding: '10px 12px' }}>Current Duration</th>
                <th style={{ padding: '10px 12px' }}>Solver Green</th>
                <th style={{ padding: '10px 12px' }}>Mean Queue</th>
                <th style={{ padding: '10px 12px' }}>Queue Load</th>
                <th style={{ padding: '10px 12px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(intersections)
                .filter((node) => !node.isHospital)
                .map((node) => {
                  const isSelected = selectedIntersectionId === node.id;
                  return (
                    <tr
                      key={node.id}
                      style={{
                        borderBottom: '1px solid rgba(139, 92, 246, 0.08)',
                        background: isSelected ? 'rgba(82, 39, 255, 0.15)' : 'transparent',
                        cursor: 'pointer',
                        transition: 'background 0.15s',
                      }}
                      onClick={() => setSelectedIntersectionId(node.id)}
                    >
                      <td style={{ padding: '12px', fontWeight: 700, color: '#fff' }}>
                        <span style={{
                          background: 'rgba(82, 39, 255, 0.25)',
                          border: '1px solid rgba(168, 85, 247, 0.4)',
                          color: '#c4b5fd',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          marginRight: '8px',
                          fontSize: '0.75rem',
                        }}>
                          {node.id}
                        </span>
                        {node.name}
                      </td>
                      <td style={{ padding: '12px' }}>{getSignalBadge(node.signal)}</td>
                      <td style={{ padding: '12px' }}>{node.optimizedSignal ? getSignalBadge(node.optimizedSignal) : <span style={{ color: 'rgba(196,181,253,.6)' }}>run optimiser</span>}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: '#00f5ff' }}>
                        {node.signalDuration}s
                      </td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: '#10b981', fontWeight: 700 }}>
                        {node.optimizedDuration === undefined ? '—' : `${node.optimizedDuration}s`}
                      </td>
                      <td style={{ padding: '12px', fontWeight: 700, color: node.queue > 30 ? '#ef4444' : '#fff' }}>
                        {node.queue} veh
                      </td>
                      <td style={{ padding: '12px', fontWeight: 700, color: node.density > 80 ? '#ef4444' : '#10b981' }}>
                        {node.density}%
                      </td>
                      <td style={{ padding: '12px' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedIntersectionId(node.id);
                          }}
                          style={{
                            background: 'rgba(82, 39, 255, 0.2)',
                            border: '1px solid rgba(168, 85, 247, 0.3)',
                            color: '#c4b5fd',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
