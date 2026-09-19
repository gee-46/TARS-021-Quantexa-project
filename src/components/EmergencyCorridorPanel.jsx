import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import { Ambulance, ShieldAlert, CheckCircle2, RotateCcw, ArrowRight, Clock, MapPin, Zap } from 'lucide-react';

export default function EmergencyCorridorPanel() {
  const {
    emergencyCorridorActive,
    handleActivateCorridor,
    handleRestoreTraffic,
  } = useTraffic();

  return (
    <div style={{
      background: emergencyCorridorActive
        ? 'linear-gradient(135deg, rgba(35, 12, 25, 0.95) 0%, rgba(12, 8, 24, 0.98) 100%)'
        : 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
      border: emergencyCorridorActive
        ? '1px solid rgba(239, 68, 68, 0.5)'
        : '1px solid rgba(139, 92, 246, 0.25)',
      borderRadius: '16px',
      padding: '22px',
      backdropFilter: 'blur(16px)',
      boxShadow: emergencyCorridorActive
        ? '0 8px 32px rgba(239, 68, 68, 0.25)'
        : '0 8px 32px rgba(0, 0, 0, 0.4)',
      display: 'flex',
      flexDirection: 'column',
      gap: '18px',
      transition: 'all 0.3s ease',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: emergencyCorridorActive ? '#ef4444' : 'linear-gradient(135deg, #5227FF, #A855F7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: emergencyCorridorActive ? '0 0 16px rgba(239, 68, 68, 0.6)' : 'none',
          }}>
            <Ambulance size={20} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>
              EMERGENCY GREEN CORRIDOR
            </div>
            <div style={{ fontSize: '0.72rem', color: emergencyCorridorActive ? '#fca5a5' : '#c4b5fd' }}>
              Priority Preemption System for Emergency First Responders
            </div>
          </div>
        </div>

        {emergencyCorridorActive && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 12px',
            borderRadius: '20px',
            background: 'rgba(239, 68, 68, 0.2)',
            border: '1px solid #ef4444',
            color: '#fca5a5',
            fontSize: '0.75rem',
            fontWeight: 700,
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444', animation: 'pulse 1s infinite' }} />
            ACTIVE PREEMPTION
          </div>
        )}
      </div>

      {/* Ambulance Dispatch Card */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.35)',
        border: '1px solid rgba(139, 92, 246, 0.15)',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '0.82rem',
              fontWeight: 800,
              color: '#fff',
              background: 'rgba(239, 68, 68, 0.3)',
              border: '1px solid rgba(239, 68, 68, 0.5)',
              padding: '2px 8px',
              borderRadius: '4px',
            }}>
              AMBULANCE A-17
            </span>
            <span style={{ fontSize: '0.78rem', color: 'rgba(226, 232, 240, 0.8)' }}>
              Priority Code 1 (Critical Transit)
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 600 }}>
            GPS Telemetry Locked
          </span>
        </div>

        {/* Route Points */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          fontSize: '0.8rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={16} color="#ef4444" />
            <div>
              <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Origin</div>
              <div style={{ fontWeight: 700, color: '#fff' }}>I1 (Cyber Central North)</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={16} color="#10b981" />
            <div>
              <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Destination</div>
              <div style={{ fontWeight: 700, color: '#fff' }}>City General Hospital</div>
            </div>
          </div>
        </div>

        {/* Active Route Nodes Sequence */}
        <div style={{
          background: 'rgba(82, 39, 255, 0.1)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          borderRadius: '8px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.8rem',
          fontWeight: 700,
        }}>
          <span style={{ color: emergencyCorridorActive ? '#6ee7b7' : '#c4b5fd' }}>I1</span>
          <ArrowRight size={14} color="rgba(139, 92, 246, 0.6)" />
          <span style={{ color: emergencyCorridorActive ? '#6ee7b7' : '#c4b5fd' }}>I2</span>
          <ArrowRight size={14} color="rgba(139, 92, 246, 0.6)" />
          <span style={{ color: emergencyCorridorActive ? '#6ee7b7' : '#c4b5fd' }}>I5</span>
          <ArrowRight size={14} color="rgba(139, 92, 246, 0.6)" />
          <span style={{ color: emergencyCorridorActive ? '#6ee7b7' : '#c4b5fd' }}>I4</span>
          <ArrowRight size={14} color="rgba(139, 92, 246, 0.6)" />
          <span style={{ color: '#f472b6' }}>HOSPITAL</span>
        </div>
      </div>

      {/* ETA Comparison */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '10px',
      }}>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.12)' }}>
          <div style={{ fontSize: '0.68rem', color: 'rgba(196, 181, 253, 0.7)' }}>Standard Transit ETA</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'rgba(255, 255, 255, 0.7)', marginTop: '2px' }}>
            11m 42s
          </div>
        </div>

        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
          <div style={{ fontSize: '0.68rem', color: '#6ee7b7' }}>Green Corridor ETA</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
            7m 18s
          </div>
        </div>

        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(0, 245, 255, 0.25)' }}>
          <div style={{ fontSize: '0.68rem', color: '#38bdf8' }}>Emergency Time Saved</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#00f5ff', marginTop: '2px' }}>
            4m 24s <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>(-37.6%)</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '12px' }}>
        {!emergencyCorridorActive ? (
          <button
            onClick={handleActivateCorridor}
            style={{
              flex: 1,
              padding: '14px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
              border: 'none',
              color: '#fff',
              fontWeight: 800,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 0 24px rgba(239, 68, 68, 0.4)',
              transition: 'all 0.2s',
            }}
          >
            <Zap size={18} />
            <span>ACTIVATE GREEN CORRIDOR</span>
          </button>
        ) : (
          <button
            onClick={handleRestoreTraffic}
            style={{
              flex: 1,
              padding: '14px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              border: 'none',
              color: '#fff',
              fontWeight: 800,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 0 24px rgba(16, 185, 129, 0.4)',
              transition: 'all 0.2s',
            }}
          >
            <RotateCcw size={18} />
            <span>RESTORE NORMAL TRAFFIC</span>
          </button>
        )}
      </div>
    </div>
  );
}
