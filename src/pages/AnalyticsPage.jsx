import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import { getAnalyticsData } from '../services/api';
import { BarChart3, TrendingDown, TrendingUp, CloudSun, Fuel, Timer, Car, ArrowDownRight } from 'lucide-react';

export default function AnalyticsPage() {
  const { isOptimized } = useTraffic();
  const data = getAnalyticsData(isOptimized);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BarChart3 size={24} color="#00f5ff" />
            TRAFFIC ANALYTICS & EMISSIONS BENCHMARKS
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'rgba(216, 207, 247, 0.75)', margin: '4px 0 0 0' }}>
            Multi-Dimensional Impact Analysis: Congestion, Fuel Consumption, CO₂ Reductions, and Throughput Gains
          </p>
        </div>

        <span style={{
          fontSize: '0.78rem',
          fontWeight: 700,
          background: isOptimized ? 'rgba(16, 185, 129, 0.2)' : 'rgba(82, 39, 255, 0.2)',
          border: `1px solid ${isOptimized ? '#10b981' : '#a855f7'}`,
          color: isOptimized ? '#6ee7b7' : '#c4b5fd',
          padding: '6px 14px',
          borderRadius: '20px',
        }}>
          {isOptimized ? '● Displaying Post-Optimization State' : '● Baseline Comparison Mode'}
        </span>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {data.kpiComparisons.map((kpi) => (
          <div
            key={kpi.metric}
            style={{
              background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              borderRadius: '12px',
              padding: '16px',
              backdropFilter: 'blur(12px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(196, 181, 253, 0.8)' }}>
              {kpi.metric}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'rgba(255, 255, 255, 0.5)' }}>Classical Fixed</div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'rgba(255, 255, 255, 0.7)' }}>
                  {kpi.classical}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.68rem', color: '#a78bfa' }}>Hybrid QAOA</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#00f5ff' }}>
                  {kpi.quantum}
                </div>
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                background: 'rgba(16, 185, 129, 0.2)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#6ee7b7',
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: 800,
              }}>
                <ArrowDownRight size={14} />
                {kpi.diff}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '20px' }}>
        {/* Time Series Waiting Time Chart */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          borderRadius: '16px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff' }}>
              PEAK HOUR WAITING TIME PROFILE (08:00 - 09:30)
            </div>
            <div style={{ display: 'flex', gap: '14px', fontSize: '0.72rem' }}>
              <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '8px', height: '8px', background: '#ef4444', borderRadius: '2px' }} />
                Fixed Classical
              </span>
              <span style={{ color: '#00f5ff', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '8px', height: '8px', background: '#00f5ff', borderRadius: '2px' }} />
                Hybrid QAOA
              </span>
            </div>
          </div>

          {/* SVG Bar Comparison Chart */}
          <div style={{ height: '220px', width: '100%' }}>
            <svg viewBox="0 0 600 220" style={{ width: '100%', height: '100%' }}>
              {/* Grid Lines */}
              {[40, 90, 140, 190].map((y, idx) => (
                <line key={idx} x1="40" y1={y} x2="580" y2={y} stroke="rgba(139, 92, 246, 0.12)" strokeDasharray="4,4" />
              ))}

              {data.timeSeries.map((item, idx) => {
                const x = 70 + idx * 85;
                const hClassical = (item.classicalWait / 100) * 150;
                const hQuantum = (item.quantumWait / 100) * 150;

                return (
                  <g key={item.time}>
                    {/* Classical Bar */}
                    <rect
                      x={x - 14}
                      y={190 - hClassical}
                      width="12"
                      height={hClassical}
                      rx="3"
                      fill="rgba(239, 68, 68, 0.7)"
                    />
                    {/* Quantum Bar */}
                    <rect
                      x={x + 2}
                      y={190 - hQuantum}
                      width="12"
                      height={hQuantum}
                      rx="3"
                      fill="url(#cyanBarGrad)"
                    />
                    {/* Time Label */}
                    <text x={x} y="208" fill="rgba(196, 181, 253, 0.7)" fontSize="10" textAnchor="middle">
                      {item.time}
                    </text>
                  </g>
                );
              })}

              <defs>
                <linearGradient id="cyanBarGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00f5ff" />
                  <stop offset="100%" stopColor="#5227FF" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        {/* Environmental & Fuel Emissions Table */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(16, 12, 34, 0.95) 0%, rgba(8, 6, 18, 0.98) 100%)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          borderRadius: '16px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CloudSun size={18} color="#10b981" />
            EMISSIONS & FUEL REDUCTION AUDIT
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.emissionsData.map((row) => (
              <div
                key={row.category}
                style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(139, 92, 246, 0.12)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff' }}>{row.category}</div>
                  <div style={{ fontSize: '0.72rem', color: 'rgba(196, 181, 253, 0.7)' }}>
                    {row.classical} → <strong style={{ color: '#00f5ff' }}>{row.quantum}</strong>
                  </div>
                </div>

                <span style={{
                  fontSize: '0.85rem',
                  fontWeight: 800,
                  color: '#10b981',
                  background: 'rgba(16, 185, 129, 0.15)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}>
                  {row.improvement}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
