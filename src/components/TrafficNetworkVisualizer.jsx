import React, { useState, useEffect } from 'react';
import { useTraffic } from '../context/TrafficContext';
import { Ambulance, AlertCircle, Sparkles, Navigation } from 'lucide-react';

export default function TrafficNetworkVisualizer() {
  const {
    intersections,
    roads,
    selectedIntersectionId,
    setSelectedIntersectionId,
    emergencyCorridorActive,
    emergencyRoutes,
  } = useTraffic();

  const [particleOffset, setParticleOffset] = useState(0);

  // Animated traffic flow loop
  useEffect(() => {
    let animFrame;
    const animate = () => {
      setParticleOffset((prev) => (prev + 0.008) % 1);
      animFrame = requestAnimationFrame(animate);
    };
    animFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animFrame);
  }, []);

  const getNodeColor = (node) => {
    if (node.isHospital) return '#ec4899';
    if (node.density >= 85) return '#ef4444'; // Red (Congestion)
    if (node.density >= 55) return '#f59e0b'; // Yellow (Warning)
    return '#10b981'; // Green (Smooth)
  };

  const getSignalBadgeColor = (signal) => {
    if (signal === 'GREEN') return '#10b981';
    if (signal === 'YELLOW') return '#f59e0b';
    return '#ef4444';
  };

  const isEdgeInCorridor = (fromId, toId) => {
    if (!emergencyCorridorActive) return false;
    return emergencyRoutes.some(({ route }) =>
      route.some(
        (id, i) =>
          i < route.length - 1 &&
          ((id === fromId && route[i + 1] === toId) || (id === toId && route[i + 1] === fromId)),
      ),
    );
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      minHeight: '520px',
      background: 'radial-gradient(ellipse at 50% 40%, rgba(20, 15, 45, 0.95) 0%, rgba(7, 6, 18, 0.98) 100%)',
      border: '1px solid rgba(139, 92, 246, 0.22)',
      borderRadius: '16px',
      position: 'relative',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Visualizer Top Bar Controls */}
      <div style={{
        padding: '12px 18px',
        borderBottom: '1px solid rgba(139, 92, 246, 0.15)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(0, 0, 0, 0.25)',
        backdropFilter: 'blur(10px)',
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Navigation size={16} color="#00f5ff" />
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.02em' }}>
            ARTERIAL TOPOLOGY & SIMULATED QUEUE LOAD
          </span>
          <span style={{
            fontSize: '0.68rem',
            background: 'rgba(0, 245, 255, 0.15)',
            border: '1px solid rgba(0, 245, 255, 0.4)',
            color: '#38bdf8',
            padding: '2px 8px',
            borderRadius: '4px',
            fontWeight: 600,
          }}>
            Simulated arterial
          </span>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.72rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
            <span style={{ color: 'rgba(226, 232, 240, 0.8)' }}>Free Flow (&lt;55%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
            <span style={{ color: 'rgba(226, 232, 240, 0.8)' }}>Warning (55-85%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
            <span style={{ color: 'rgba(226, 232, 240, 0.8)' }}>Congested (&gt;85%)</span>
          </div>
          {emergencyCorridorActive && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '2px 8px',
              borderRadius: '4px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid #ef4444',
              color: '#fca5a5',
              fontWeight: 700,
            }}>
              <Ambulance size={12} color="#ef4444" />
              <span>{emergencyRoutes.map((r) => r.id).join(', ')} routed</span>
            </div>
          )}
        </div>
      </div>

      {/* SVG Canvas for Network Graph */}
      <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        <svg
          viewBox="0 0 1000 620"
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
          }}
        >
          <defs>
            {/* Grid Pattern */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(139, 92, 246, 0.06)" strokeWidth="1" />
            </pattern>

            {/* Glow Filters */}
            <filter id="cyanGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="greenGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="redGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background Grid */}
          <rect width="1000" height="620" fill="url(#grid)" />

          {/* Render Roads (Edges) */}
          {roads.map((road) => {
            const fromNode = intersections[road.from];
            const toNode = intersections[road.to];
            if (!fromNode || !toNode) return null;

            const isCorridor = isEdgeInCorridor(road.from, road.to);
            const isCongested = road.congestion === 'high' || fromNode.density > 85;
            const isBlocked = road.congestion === 'blocked' || road.congestion === 'closed';

            let strokeColor = 'rgba(139, 92, 246, 0.35)';
            let strokeWidth = 5;

            if (isCorridor) {
              strokeColor = '#10b981';
              strokeWidth = 7;
            } else if (isBlocked) {
              strokeColor = '#ef4444';
              strokeWidth = 4;
            } else if (isCongested) {
              strokeColor = '#f59e0b';
              strokeWidth = 5;
            }

            // Calculate particle positions along edge
            const numParticles = 3;
            const particles = [];
            for (let i = 0; i < numParticles; i++) {
              const t = (particleOffset + i / numParticles) % 1;
              const px = fromNode.x + (toNode.x - fromNode.x) * t;
              const py = fromNode.y + (toNode.y - fromNode.y) * t;
              particles.push({ px, py });
            }

            return (
              <g key={road.id}>
                {/* Road Line Base */}
                <line
                  x1={fromNode.x}
                  y1={fromNode.y}
                  x2={toNode.x}
                  y2={toNode.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={isBlocked ? '6,6' : 'none'}
                  strokeLinecap="round"
                  filter={isCorridor ? 'url(#greenGlow)' : undefined}
                />

                {/* Road Name Label */}
                <text
                  x={(fromNode.x + toNode.x) / 2}
                  y={(fromNode.y + toNode.y) / 2 - 8}
                  fill="rgba(196, 181, 253, 0.6)"
                  fontSize="9"
                  fontFamily="sans-serif"
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {road.name}
                </text>

                {/* Flow Particles */}
                {!isBlocked &&
                  particles.map((p, pIdx) => (
                    <circle
                      key={pIdx}
                      cx={p.px}
                      cy={p.py}
                      r={isCorridor ? 4 : 2.8}
                      fill={isCorridor ? '#00f5ff' : isCongested ? '#fbbf24' : '#c084fc'}
                      filter="url(#cyanGlow)"
                    />
                  ))}
              </g>
            );
          })}

          {/* Render Intersection Nodes */}
          {Object.values(intersections).map((node) => {
            const isSelected = selectedIntersectionId === node.id;
            const nodeColor = getNodeColor(node);
            const signalColor = getSignalBadgeColor(node.signal);
            const isCorridorNode = emergencyCorridorActive && emergencyRoutes.some(({ route }) => route.includes(node.id));

            return (
              <g
                key={node.id}
                onClick={() => setSelectedIntersectionId(node.id)}
                style={{ cursor: 'pointer' }}
              >
                {/* Selection / Highlight Pulse Ring */}
                {isSelected && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="46"
                    fill="none"
                    stroke="#00f5ff"
                    strokeWidth="2"
                    strokeDasharray="4,4"
                    filter="url(#cyanGlow)"
                  />
                )}

                {/* Emergency Corridor Glow Ring */}
                {isCorridorNode && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="42"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="3"
                    filter="url(#greenGlow)"
                  />
                )}

                {/* Node Outer Circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="34"
                  fill="rgba(13, 10, 30, 0.95)"
                  stroke={nodeColor}
                  strokeWidth={isSelected ? 3 : 2}
                  filter={node.density >= 85 ? 'url(#redGlow)' : undefined}
                />

                {/* Inner Data Display */}
                {node.isHospital ? (
                  <>
                    <text
                      x={node.x}
                      y={node.y - 4}
                      fill="#fff"
                      fontSize="11"
                      fontWeight="800"
                      textAnchor="middle"
                    >
                      HOSPITAL
                    </text>
                    <text
                      x={node.x}
                      y={node.y + 12}
                      fill="#f472b6"
                      fontSize="9"
                      fontWeight="700"
                      textAnchor="middle"
                    >
                      EMERGENCY
                    </text>
                  </>
                ) : (
                  <>
                    {/* Intersection ID */}
                    <text
                      x={node.x}
                      y={node.y - 12}
                      fill="#fff"
                      fontSize="12"
                      fontWeight="800"
                      textAnchor="middle"
                    >
                      {node.id}
                    </text>

                    {/* Density & Queue */}
                    <text
                      x={node.x}
                      y={node.y + 2}
                      fill={nodeColor}
                      fontSize="10"
                      fontWeight="700"
                      textAnchor="middle"
                    >
                      {node.density}%
                    </text>

                    <text
                      x={node.x}
                      y={node.y + 15}
                      fill="rgba(216, 207, 247, 0.8)"
                      fontSize="8.5"
                      fontWeight="600"
                      textAnchor="middle"
                    >
                      {node.queue} veh
                    </text>

                    {/* Signal Status LED */}
                    <circle
                      cx={node.x + 22}
                      cy={node.y - 20}
                      r="6"
                      fill={signalColor}
                      stroke="#000"
                      strokeWidth="1.5"
                    />
                  </>
                )}

                {/* Node Tag / Name pill below */}
                <rect
                  x={node.x - 55}
                  y={node.y + 38}
                  width="110"
                  height="18"
                  rx="4"
                  fill="rgba(10, 8, 24, 0.85)"
                  stroke="rgba(139, 92, 246, 0.25)"
                />
                <text
                  x={node.x}
                  y={node.y + 50}
                  fill="rgba(241, 245, 249, 0.9)"
                  fontSize="8"
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {node.name.length > 20 ? `${node.name.substring(0, 18)}...` : node.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Live Interaction Hint */}
        <div style={{
          position: 'absolute',
          bottom: '12px',
          left: '16px',
          fontSize: '0.72rem',
          color: 'rgba(196, 181, 253, 0.7)',
          background: 'rgba(0, 0, 0, 0.5)',
          padding: '4px 10px',
          borderRadius: '6px',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <Sparkles size={12} color="#00f5ff" />
          <span>Click a junction to inspect its simulated queue, waits and signal plan</span>
        </div>
      </div>
    </div>
  );
}
