import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import { Activity, Clock, ShieldCheck, Gauge, ArrowRight, X } from 'lucide-react';

export default function IntersectionDetailModal() {
  const { selectedIntersection, isOptimized, emergencyCorridorActive } = useTraffic();

  if (!selectedIntersection) return null;

  const getSignalColor = (sig) => {
    if (sig === 'GREEN') return '#10b981';
    if (sig === 'YELLOW') return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
      border: '1px solid rgba(139, 92, 246, 0.22)',
      borderRadius: '14px',
      padding: '18px',
      backdropFilter: 'blur(16px)',
      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4)',
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '1.1rem',
              fontWeight: 800,
              color: '#fff',
              background: 'linear-gradient(90deg, #5227FF, #A855F7)',
              padding: '2px 8px',
              borderRadius: '6px',
            }}>
              {selectedIntersection.id}
            </span>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
              {selectedIntersection.name}
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'rgba(196, 181, 253, 0.7)', marginTop: '4px' }}>
            Phase: {selectedIntersection.phase || 'Dynamic Adaptive Phase'}
          </div>
        </div>

        {/* Current Signal LED Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 10px',
          borderRadius: '6px',
          background: `${getSignalColor(selectedIntersection.signal)}20`,
          border: `1px solid ${getSignalColor(selectedIntersection.signal)}`,
          color: getSignalColor(selectedIntersection.signal),
          fontWeight: 700,
          fontSize: '0.78rem',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: getSignalColor(selectedIntersection.signal),
            boxShadow: `0 0 10px ${getSignalColor(selectedIntersection.signal)}`,
          }} />
          {selectedIntersection.signal}
        </div>
      </div>

      {/* Capacity & Density Progress Bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
          <span style={{ color: 'rgba(216, 207, 247, 0.8)' }}>Road Capacity Utilization</span>
          <span style={{ fontWeight: 700, color: selectedIntersection.capacity > 85 ? '#ef4444' : '#00f5ff' }}>
            {selectedIntersection.capacity}% ({selectedIntersection.queue} / {Math.round(selectedIntersection.capacity * 1.3)} vehicles)
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '8px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${selectedIntersection.capacity}%`,
            height: '100%',
            background: selectedIntersection.capacity > 85
              ? 'linear-gradient(90deg, #f59e0b, #ef4444)'
              : 'linear-gradient(90deg, #5227FF, #00f5ff)',
            borderRadius: '4px',
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>

      {/* Key Metric Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '10px',
      }}>
        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(139, 92, 246, 0.12)',
          borderRadius: '8px',
          padding: '10px',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Traffic Density</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', marginTop: '2px' }}>
            {selectedIntersection.density}%
          </div>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(139, 92, 246, 0.12)',
          borderRadius: '8px',
          padding: '10px',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Queue Length</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', marginTop: '2px' }}>
            {selectedIntersection.queue} <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#a78bfa' }}>veh</span>
          </div>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(139, 92, 246, 0.12)',
          borderRadius: '8px',
          padding: '10px',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Current Green Duration</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#00f5ff', marginTop: '2px' }}>
            {selectedIntersection.signalDuration}s
          </div>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(139, 92, 246, 0.12)',
          borderRadius: '8px',
          padding: '10px',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>QAOA Optimal Duration</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
            {selectedIntersection.optimizedDuration || 60}s
          </div>
        </div>
      </div>

      {/* Connected Arteries */}
      <div style={{
        fontSize: '0.72rem',
        color: 'rgba(196, 181, 253, 0.8)',
        background: 'rgba(82, 39, 255, 0.1)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '6px',
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span>Connected Hubs: <strong>{selectedIntersection.connectedTo?.join(' ↔ ') || 'None'}</strong></span>
        <span>Lanes: <strong>{selectedIntersection.lanes || 4}</strong></span>
      </div>
    </div>
  );
}
