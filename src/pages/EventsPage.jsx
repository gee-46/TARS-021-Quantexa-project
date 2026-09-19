import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import { AlertTriangle, Car, Flame, Construction, Siren, CheckCircle2, Cpu, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function EventsPage() {
  const { activeEvents, handleTriggerEvent } = useTraffic();

  const eventTypes = [
    {
      id: 'CONGESTION',
      title: 'SUDDEN CONGESTION',
      desc: 'Inject surge volume along West Corridor (I1 - I3)',
      icon: Car,
      color: '#f59e0b',
      border: 'rgba(245, 158, 11, 0.4)',
    },
    {
      id: 'ACCIDENT',
      title: 'COLLISION / ACCIDENT',
      desc: 'Block 2 lanes at I3 (Quantum Plaza) causing severe queue lock',
      icon: Flame,
      color: '#ef4444',
      border: 'rgba(239, 68, 68, 0.4)',
    },
    {
      id: 'ROAD_CLOSURE',
      title: 'ROAD CLOSURE',
      desc: 'Simulate municipal roadwork closure on South Valley Way (R5)',
      icon: Construction,
      color: '#a855f7',
      border: 'rgba(168, 85, 247, 0.4)',
    },
    {
      id: 'EMERGENCY_VEHICLE',
      title: 'EMERGENCY VEHICLE',
      desc: 'Dispatch Ambulance A-17 with priority routing to City Hospital',
      icon: Siren,
      color: '#00f5ff',
      border: 'rgba(0, 245, 255, 0.4)',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertTriangle size={24} color="#f59e0b" />
          DYNAMIC TRAFFIC EVENTS & DISRUPTION INJECTION
        </h1>
        <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>
          Simulate Real-Time Urban Incidents and Validate Hybrid Quantum Adaptive Re-Optimization
        </p>
      </div>

      {/* Trigger Event Action Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '16px',
      }}>
        {eventTypes.map((evt) => {
          const Icon = evt.icon;
          return (
            <div
              key={evt.id}
              style={{
                background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
                border: `1px solid ${evt.border}`,
                borderRadius: '14px',
                padding: '18px',
                backdropFilter: 'blur(12px)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '14px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: '8px',
                    background: `${evt.color}20`,
                    border: `1px solid ${evt.color}50`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <Icon size={18} color={evt.color} />
                  </div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>
                    {evt.title}
                  </div>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(196, 181, 253, 0.8)', marginTop: '8px', lineHeight: 1.4 }}>
                  {evt.desc}
                </div>
              </div>

              <button
                onClick={() => handleTriggerEvent(evt.id)}
                style={{
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: `linear-gradient(135deg, ${evt.color} 0%, rgba(82, 39, 255, 0.8) 100%)`,
                  border: 'none',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  boxShadow: `0 0 16px ${evt.color}40`,
                  transition: 'transform 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              >
                <span>Trigger Incident Event</span>
              </button>
            </div>
          );
        })}
      </div>

      {/* System Response Workflow Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(82, 39, 255, 0.15) 0%, rgba(16, 12, 34, 0.95) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.3)',
        borderRadius: '14px',
        padding: '18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #5227FF, #A855F7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Cpu size={22} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff' }}>
              Adaptive Response System
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(216, 207, 247, 0.85)' }}>
              When an event occurs: <strong>✓ Event detected</strong> → <strong>✓ Network updated</strong> → <strong>✓ Optimization recommended</strong>
            </div>
          </div>
        </div>

        <Link
          to="/quantum"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'linear-gradient(135deg, #5227FF, #A855F7)',
            color: '#fff',
            padding: '10px 18px',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 700,
            textDecoration: 'none',
          }}
        >
          <span>Open Quantum Optimizer</span>
          <ArrowRight size={15} />
        </Link>
      </div>

      {/* Live Incidents Log */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '16px',
        padding: '20px',
        backdropFilter: 'blur(16px)',
      }}>
        <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', marginBottom: '14px' }}>
          LIVE INCIDENT AUDIT STREAM
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {activeEvents.map((evt) => (
            <div
              key={evt.id}
              style={{
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid rgba(139, 92, 246, 0.15)',
                borderRadius: '8px',
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: evt.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(82, 39, 255, 0.3)',
                  color: evt.severity === 'CRITICAL' ? '#fca5a5' : '#c4b5fd',
                  border: `1px solid ${evt.severity === 'CRITICAL' ? '#ef4444' : '#a855f7'}`,
                }}>
                  {evt.severity || 'INFO'}
                </span>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>
                    {evt.title}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(196, 181, 253, 0.8)', marginTop: '2px' }}>
                    {evt.location} — {evt.description}
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '0.72rem', color: 'rgba(226, 232, 240, 0.6)', fontFamily: 'monospace' }}>
                {evt.timestamp}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
