import React from 'react';
import { Timer, Car, TrendingUp, Fuel, CloudSun, Ambulance, ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { BASELINE_METRICS } from '../services/api';

export default function KpiCards() {
  const { metrics, isOptimized, emergencyCorridorActive } = useTraffic();

  const cards = [
    {
      id: 'wait-time',
      title: 'Average Waiting Time',
      value: `${metrics.avgWaitTime.toFixed(1)}s`,
      baseline: `${BASELINE_METRICS.avgWaitTime}s`,
      change: `${(((metrics.avgWaitTime - BASELINE_METRICS.avgWaitTime) / BASELINE_METRICS.avgWaitTime) * 100).toFixed(1)}%`,
      isGoodChange: metrics.avgWaitTime <= BASELINE_METRICS.avgWaitTime,
      icon: Timer,
      color: '#00f5ff',
      tag: 'Live Signal Delay',
    },
    {
      id: 'queue-length',
      title: 'Total Queue Length',
      value: `${metrics.queueLength} veh`,
      baseline: `${BASELINE_METRICS.queueLength} veh`,
      change: `${(((metrics.queueLength - BASELINE_METRICS.queueLength) / BASELINE_METRICS.queueLength) * 100).toFixed(1)}%`,
      isGoodChange: metrics.queueLength <= BASELINE_METRICS.queueLength,
      icon: Car,
      color: '#a855f7',
      tag: '6 Hub Accumulation',
    },
    {
      id: 'throughput',
      title: 'Traffic Throughput',
      value: `${metrics.throughput} v/h`,
      baseline: `${BASELINE_METRICS.throughput} v/h`,
      change: `${(((metrics.throughput - BASELINE_METRICS.throughput) / BASELINE_METRICS.throughput) * 100).toFixed(1)}%`,
      isGoodChange: metrics.throughput >= BASELINE_METRICS.throughput,
      icon: TrendingUp,
      color: '#10b981',
      tag: 'Discharge Flow Rate',
    },
    {
      id: 'fuel',
      title: 'Fuel Consumption',
      value: `${metrics.fuelConsumption.toFixed(1)} L/h`,
      baseline: `${BASELINE_METRICS.fuelConsumption} L/h`,
      change: `${(((metrics.fuelConsumption - BASELINE_METRICS.fuelConsumption) / BASELINE_METRICS.fuelConsumption) * 100).toFixed(1)}%`,
      isGoodChange: metrics.fuelConsumption <= BASELINE_METRICS.fuelConsumption,
      icon: Fuel,
      color: '#f59e0b',
      tag: 'Stop-and-Go Loss',
    },
    {
      id: 'co2',
      title: 'CO₂ Emissions',
      value: `${metrics.co2Emissions.toFixed(0)} kg/h`,
      baseline: `${BASELINE_METRICS.co2Emissions} kg/h`,
      change: `${(((metrics.co2Emissions - BASELINE_METRICS.co2Emissions) / BASELINE_METRICS.co2Emissions) * 100).toFixed(1)}%`,
      isGoodChange: metrics.co2Emissions <= BASELINE_METRICS.co2Emissions,
      icon: CloudSun,
      color: '#38bdf8',
      tag: 'Urban Carbon Footprint',
    },
    {
      id: 'emergency-eta',
      title: 'Emergency ETA (A-17)',
      value: emergencyCorridorActive ? '7m 18s' : metrics.emergencyEta,
      baseline: BASELINE_METRICS.emergencyEta,
      change: emergencyCorridorActive ? '-37.6%' : '0.0%',
      isGoodChange: true,
      icon: Ambulance,
      color: emergencyCorridorActive ? '#ef4444' : '#c084fc',
      tag: emergencyCorridorActive ? 'GREEN CORRIDOR' : 'Normal Transit',
      highlight: emergencyCorridorActive,
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '14px',
      width: '100%',
    }}>
      {cards.map((card) => {
        const Icon = card.icon;
        const changeNum = parseFloat(card.change);
        const isBetter = card.isGoodChange;

        return (
          <div
            key={card.id}
            style={{
              background: card.highlight
                ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(20, 10, 30, 0.9) 100%)'
                : 'linear-gradient(135deg, rgba(18, 14, 38, 0.85) 0%, rgba(10, 8, 22, 0.92) 100%)',
              border: card.highlight
                ? '1px solid rgba(239, 68, 68, 0.5)'
                : '1px solid rgba(139, 92, 246, 0.18)',
              borderRadius: '12px',
              padding: '16px',
              backdropFilter: 'blur(12px)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '10px',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Top Accent Light */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: '15%',
              width: '70%',
              height: '1px',
              background: `linear-gradient(90deg, transparent, ${card.color}, transparent)`,
            }} />

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'rgba(216, 207, 247, 0.7)' }}>
                  {card.title}
                </div>
                <div style={{ fontSize: '0.62rem', color: card.color, fontWeight: 700, letterSpacing: '0.04em', marginTop: '2px' }}>
                  {card.tag}
                </div>
              </div>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: `rgba(${card.color === '#ef4444' ? '239,68,68' : '82,39,255'}, 0.2)`,
                border: `1px solid ${card.color}40`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Icon size={16} color={card.color} />
              </div>
            </div>

            {/* Main Value */}
            <div>
              <div style={{
                fontSize: '1.45rem',
                fontWeight: 800,
                color: '#fff',
                letterSpacing: '-0.02em',
                fontFamily: 'system-ui, -apple-system, sans-serif',
              }}>
                {card.value}
              </div>

              {/* Baseline & Change */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '6px',
                fontSize: '0.7rem',
              }}>
                <span style={{ color: 'rgba(167, 139, 250, 0.6)' }}>
                  Base: {card.baseline}
                </span>

                <span style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '2px',
                  fontWeight: 700,
                  color: isBetter ? '#10b981' : '#ef4444',
                }}>
                  {isBetter ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}
                  {card.change}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
