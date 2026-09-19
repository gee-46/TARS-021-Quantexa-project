import React from 'react';
import { Activity, Clock, Cpu, Server, X, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';

export default function TopStatusBar() {
  const {
    simulationTime,
    systemStatus,
    quantumEngineStatus,
    isOptimized,
    emergencyCorridorActive,
    latestNotification,
    dismissNotification,
  } = useTraffic();

  return (
    <header style={{
      height: '64px',
      background: 'rgba(10, 8, 22, 0.85)',
      borderBottom: '1px solid rgba(139, 92, 246, 0.15)',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      position: 'relative',
      zIndex: 30,
    }}>
      {/* Title & Hub ID */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            fontSize: '0.95rem',
            fontWeight: 800,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#00f5ff',
              boxShadow: '0 0 10px #00f5ff',
            }} />
            QUANTUMFORCE TRAFFIC CONTROL CENTER
          </div>
          <span style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            background: 'rgba(82, 39, 255, 0.25)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            color: '#c4b5fd',
            padding: '3px 8px',
            borderRadius: '4px',
          }}>
            SECTOR 4-METRO
          </span>
        </div>
      </div>

      {/* Real-time Status Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {/* Active Mode Badge */}
        {emergencyCorridorActive ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '4px 10px',
            borderRadius: '6px',
            background: 'rgba(239, 68, 68, 0.2)',
            border: '1px solid rgba(239, 68, 68, 0.5)',
            color: '#fca5a5',
            animation: 'pulse 1.5s infinite',
          }}>
            <ShieldAlert size={14} color="#ef4444" />
            EMERGENCY CORRIDOR ACTIVE
          </div>
        ) : isOptimized ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '4px 10px',
            borderRadius: '6px',
            background: 'rgba(16, 185, 129, 0.2)',
            border: '1px solid rgba(16, 185, 129, 0.5)',
            color: '#6ee7b7',
          }}>
            <CheckCircle2 size={14} color="#10b981" />
            QAOA OPTIMIZED
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: '6px',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            color: '#fcd34d',
          }}>
            CLASSICAL BASELINE
          </div>
        )}

        {/* System Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          color: 'rgba(226, 232, 240, 0.8)',
        }}>
          <Server size={14} color="#10b981" />
          <span>System: <strong style={{ color: '#10b981' }}>{systemStatus}</strong></span>
        </div>

        {/* Intersections */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          color: 'rgba(226, 232, 240, 0.8)',
        }}>
          <Activity size={14} color="#00f5ff" />
          <span>Intersections: <strong style={{ color: '#fff' }}>6 Active</strong></span>
        </div>

        {/* Quantum Engine */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          color: 'rgba(226, 232, 240, 0.8)',
        }}>
          <Cpu size={14} color="#a855f7" />
          <span>Quantum Engine: <strong style={{ color: '#a855f7' }}>{quantumEngineStatus}</strong></span>
        </div>

        {/* Sim Time */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.78rem',
          fontFamily: 'monospace',
          fontWeight: 700,
          background: 'rgba(0, 0, 0, 0.5)',
          padding: '4px 10px',
          borderRadius: '6px',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          color: '#00f5ff',
        }}>
          <Clock size={14} color="#00f5ff" />
          <span>{simulationTime}</span>
        </div>
      </div>

      {/* Global Notification Banner */}
      {latestNotification && (
        <div style={{
          position: 'absolute',
          top: '68px',
          right: '24px',
          zIndex: 50,
          background: latestNotification.type === 'ERROR' || latestNotification.type === 'EMERGENCY'
            ? 'rgba(35, 10, 15, 0.95)'
            : 'rgba(15, 12, 35, 0.95)',
          border: `1px solid ${
            latestNotification.type === 'ERROR' || latestNotification.type === 'EMERGENCY'
              ? 'rgba(239, 68, 68, 0.5)'
              : 'rgba(168, 85, 247, 0.5)'
          }`,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
          borderRadius: '8px',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          maxWidth: '450px',
          backdropFilter: 'blur(16px)',
          animation: 'slideIn 0.25s ease-out',
        }}>
          <div style={{ flex: 1 }}>
            <div style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              color: latestNotification.type === 'ERROR' || latestNotification.type === 'EMERGENCY' ? '#f87171' : '#c084fc',
            }}>
              {latestNotification.title}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(241, 245, 249, 0.85)', marginTop: '2px' }}>
              {latestNotification.message}
            </div>
          </div>
          <button
            onClick={dismissNotification}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.6)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </header>
  );
}
