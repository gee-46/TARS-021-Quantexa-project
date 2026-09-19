import React from 'react';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import EmergencyCorridorPanel from '../components/EmergencyCorridorPanel';
import { useTraffic } from '../context/TrafficContext';
import { Siren, Ambulance, CheckCircle2, RotateCcw, Zap, MapPin, ArrowRight } from 'lucide-react';

export default function EmergencyCorridorPage() {
  const {
    emergencyCorridorActive,
    handleActivateCorridor,
    handleRestoreTraffic,
    intersections,
  } = useTraffic();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Siren size={24} color="#ef4444" />
            INTELLIGENT EMERGENCY GREEN CORRIDOR
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>
            Dynamic Priority Preemption Routing for Emergency Response Vehicles
          </p>
        </div>

        <div>
          {!emergencyCorridorActive ? (
            <button
              onClick={handleActivateCorridor}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                border: 'none',
                color: '#fff',
                fontWeight: 800,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 0 20px rgba(239, 68, 68, 0.4)',
              }}
            >
              <Zap size={16} />
              <span>ACTIVATE GREEN CORRIDOR</span>
            </button>
          ) : (
            <button
              onClick={handleRestoreTraffic}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                border: 'none',
                color: '#fff',
                fontWeight: 800,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 0 20px rgba(16, 185, 129, 0.4)',
              }}
            >
              <RotateCcw size={16} />
              <span>RESTORE NORMAL TRAFFIC</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Visualizer & Emergency Control */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.6fr 1fr',
        gap: '20px',
      }}>
        <TrafficNetworkVisualizer />
        <EmergencyCorridorPanel />
      </div>

      {/* Corridor Intersections Status Breakdown */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '16px',
        padding: '20px',
        backdropFilter: 'blur(16px)',
      }}>
        <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', marginBottom: '14px' }}>
          CORRIDOR PREEMPTION STAGE MONITORING (I1 → I2 → I5 → I4 → HOSPITAL)
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          {['I1', 'I2', 'I5', 'I4'].map((id) => {
            const node = intersections[id];
            return (
              <div
                key={id}
                style={{
                  background: 'rgba(0, 0, 0, 0.35)',
                  border: emergencyCorridorActive
                    ? '1px solid rgba(16, 185, 129, 0.4)'
                    : '1px solid rgba(139, 92, 246, 0.15)',
                  borderRadius: '10px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.95rem', color: '#fff' }}>{id}</span>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: emergencyCorridorActive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                    color: emergencyCorridorActive ? '#6ee7b7' : 'rgba(255, 255, 255, 0.6)',
                  }}>
                    {emergencyCorridorActive ? 'GREEN (Preempted)' : node.signal}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(196, 181, 253, 0.8)' }}>
                  {node.name}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'rgba(226, 232, 240, 0.65)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Density: {node.density}%</span>
                  <span>Queue: {node.queue} veh</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
