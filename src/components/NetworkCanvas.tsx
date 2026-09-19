import React from 'react';
import { Intersection, Road, Vehicle, EmergencyConstraints, IntersectionId, RoadId } from '../types/traffic';
import { Siren, AlertTriangle, ShieldAlert, Zap, Navigation, Clock } from 'lucide-react';

interface NetworkCanvasProps {
  intersections: Map<IntersectionId, Intersection>;
  roads: Map<RoadId, Road>;
  vehicles: Map<string, Vehicle>;
  constraints: EmergencyConstraints;
  queueJumpingEnabled: boolean;
  selectedElement: { type: 'intersection' | 'road'; id: string } | null;
  onSelectElement: (element: { type: 'intersection' | 'road'; id: string } | null) => void;
}

export const NetworkCanvas: React.FC<NetworkCanvasProps> = ({
  intersections,
  roads,
  vehicles,
  constraints,
  queueJumpingEnabled,
  selectedElement,
  onSelectElement,
}) => {
  // Find emergency hops
  const corridorHopsSet = new Set(
    constraints.corridor_hops.map(([u, v]) => `${u}->${v}`)
  );

  // Group vehicles by road
  const vehiclesByRoad = new Map<RoadId, Vehicle[]>();
  for (const road of roads.values()) {
    vehiclesByRoad.set(road.id, road.vehicles);
  }

  return (
    <div className="relative w-full h-[520px] bg-slate-900/90 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-md">
      {/* Grid Canvas Background */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
        <defs>
          <pattern id="canvas-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#64748b" strokeWidth="0.75" strokeDasharray="3 3" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#canvas-grid)" />
      </svg>

      {/* SVG Rendering for Roads, Intersections, and Vehicles */}
      <svg className="w-full h-full" viewBox="0 0 760 420">
        <defs>
          {/* Corridor Glow Filter */}
          <filter id="corridor-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          {/* Siren Glow Filter */}
          <filter id="siren-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* 1. ROADS (Directed Segments) */}
        {Array.from(roads.values()).map((road) => {
          const fromInter = intersections.get(road.from);
          const toInter = intersections.get(road.to);
          if (!fromInter || !toInter) return null;

          const isCorridor = corridorHopsSet.has(road.id);
          const isSelected = selectedElement?.type === 'road' && selectedElement.id === road.id;

          // Offset bidirectional roads slightly so both directions are distinctly visible
          const dx = toInter.x - fromInter.x;
          const dy = toInter.y - fromInter.y;
          const len = Math.hypot(dx, dy) || 1;
          const normX = -dy / len;
          const normY = dx / len;
          const offsetDist = 12; // 12px lateral offset for right-hand driving

          const x1 = fromInter.x + normX * offsetDist;
          const y1 = fromInter.y + normY * offsetDist;
          const x2 = toInter.x + normX * offsetDist;
          const y2 = toInter.y + normY * offsetDist;

          // Road coloring by status and corridor
          let strokeColor = '#334155'; // default slate-700
          if (isCorridor) {
            strokeColor = '#10b981'; // vibrant green emergency corridor
          } else if (road.status === 'accident' || road.status === 'closure') {
            strokeColor = '#ef4444'; // red hazard
          } else if (road.status === 'congestion') {
            strokeColor = '#f59e0b'; // amber congestion
          } else if (road.vehicles.length > 4) {
            strokeColor = '#eab308'; // heavy traffic
          }

          // Check if emergency vehicle is currently on this road
          const hasEmergencyVehicle = road.vehicles.some((v) => v.type !== 'normal');

          return (
            <g
              key={road.id}
              className="cursor-pointer transition-all duration-200"
              onClick={() => onSelectElement({ type: 'road', id: road.id })}
            >
              {/* Outer Road Bed */}
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={isSelected ? '#38bdf8' : '#1e293b'}
                strokeWidth={isSelected ? 26 : 22}
                strokeLinecap="round"
              />

              {/* Road Lane Surface */}
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={strokeColor}
                strokeWidth={isCorridor ? 14 : 10}
                strokeDasharray={road.status === 'congestion' ? '8 4' : road.status === 'closure' ? '4 4' : undefined}
                strokeOpacity={isCorridor ? 0.9 : 0.6}
                filter={isCorridor ? 'url(#corridor-glow)' : undefined}
              />

              {/* Center Dash for Active Corridor */}
              {isCorridor && (
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#34d399"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  className="animate-pulse"
                />
              )}

              {/* Directional Chevrons / Arrow */}
              {len > 60 && (
                <polygon
                  points={`
                    ${x1 + dx * 0.5},${y1 + dy * 0.5}
                    ${x1 + dx * 0.5 - normX * 4 - (dx / len) * 8},${y1 + dy * 0.5 - normY * 4 - (dy / len) * 8}
                    ${x1 + dx * 0.5 + normX * 4 - (dx / len) * 8},${y1 + dy * 0.5 + normY * 4 - (dy / len) * 8}
                  `}
                  fill={isCorridor ? '#34d399' : '#64748b'}
                  opacity={0.7}
                />
              )}

              {/* Hazard Icon or Capacity Badge in the middle */}
              {road.status !== 'normal' && (
                <g transform={`translate(${x1 + dx * 0.5}, ${y1 + dy * 0.5})`}>
                  <circle r={11} fill="#0f172a" stroke={road.status === 'accident' ? '#ef4444' : '#f59e0b'} strokeWidth={2} />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize="10"
                    fill={road.status === 'accident' ? '#ef4444' : '#f59e0b'}
                    fontWeight="bold"
                  >
                    {road.status === 'accident' ? '!' : road.status === 'closure' ? 'X' : '~'}
                  </text>
                </g>
              )}

              {/* Queue Length Badge (if vehicles present) */}
              {road.vehicles.length > 0 && (
                <g transform={`translate(${x1 + dx * 0.25}, ${y1 + dy * 0.25})`}>
                  <rect
                    x={-14}
                    y={-9}
                    width={28}
                    height={18}
                    rx={5}
                    fill={hasEmergencyVehicle ? '#991b1b' : '#0f172a'}
                    stroke={hasEmergencyVehicle ? '#ef4444' : '#475569'}
                    strokeWidth={1.5}
                  />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize="10"
                    fill={hasEmergencyVehicle ? '#fecaca' : '#cbd5e1'}
                    fontWeight="bold"
                    className="font-mono"
                  >
                    Q:{road.vehicles.length}
                  </text>
                </g>
              )}

              {/* 2. VEHICLES QUEUED ALONG THIS ROAD */}
              {road.vehicles.map((veh, idx) => {
                // Position vehicles queued up behind the intersection stop-line (from x2,y2 backwards)
                // idx 0 is at head of queue (nearest to toInter), idx 1 is behind it, etc.
                const stopOffset = 30; // distance before intersection center
                const vehicleSpacing = 18;
                const totalDist = stopOffset + idx * vehicleSpacing;
                const fraction = Math.max(0.1, 1.0 - totalDist / len);

                const vx = x1 + dx * fraction;
                const vy = y1 + dy * fraction;

                const isAmbulance = veh.type === 'ambulance';
                const isEmergency = veh.type !== 'normal';

                return (
                  <g key={veh.id} className="transition-all duration-300">
                    {/* Pulsing Beacon Glow for Ambulance */}
                    {isAmbulance && (
                      <circle
                        cx={vx}
                        cy={vy}
                        r={16}
                        fill="#ef4444"
                        opacity={0.35}
                        filter="url(#siren-glow)"
                        className="animate-ping"
                      />
                    )}

                    {/* Vehicle Body Capsule */}
                    <rect
                      x={vx - (isEmergency ? 10 : 7)}
                      y={vy - (isEmergency ? 6 : 4)}
                      width={isEmergency ? 20 : 14}
                      height={isEmergency ? 12 : 8}
                      rx={isEmergency ? 4 : 2}
                      fill={veh.color}
                      stroke={isEmergency ? '#ffffff' : '#475569'}
                      strokeWidth={isEmergency ? 1.5 : 1}
                      filter={isEmergency ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))' : undefined}
                    />

                    {/* Preemption Badge / Siren indicator */}
                    {isEmergency && (
                      <>
                        {/* Red/Blue Siren Flasher */}
                        <circle
                          cx={vx - 3}
                          cy={vy}
                          r={2}
                          fill="#ef4444"
                          className="animate-pulse"
                        />
                        <circle
                          cx={vx + 3}
                          cy={vy}
                          r={2}
                          fill="#38bdf8"
                          className="animate-pulse"
                        />

                        {/* Queue Jumping Preemption Flag if at front of queue */}
                        {idx === 0 && veh.queueJumpedCount > 0 && queueJumpingEnabled && (
                          <g transform={`translate(${vx}, ${vy - 16})`}>
                            <rect
                              x={-28}
                              y={-7}
                              width={56}
                              height={14}
                              rx={4}
                              fill="#dc2626"
                              stroke="#ffffff"
                              strokeWidth={1}
                            />
                            <text
                              textAnchor="middle"
                              dominantBaseline="central"
                              fontSize="8"
                              fill="#ffffff"
                              fontWeight="bold"
                              className="font-mono tracking-tighter"
                            >
                              ⚡ JUMPED
                            </text>
                          </g>
                        )}
                      </>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* 3. INTERSECTIONS (Nodes with Traffic Lights) */}
        {Array.from(intersections.values()).map((inter) => {
          const isSelected = selectedElement?.type === 'intersection' && selectedElement.id === inter.id;
          const isCorridorNode = constraints.priority_intersections.includes(inter.id);
          const activeGreenDir = inter.forcedGreen ?? inter.currentGreen;

          return (
            <g
              key={inter.id}
              className="cursor-pointer transition-transform duration-150 hover:scale-105"
              onClick={() => onSelectElement({ type: 'intersection', id: inter.id })}
            >
              {/* Outer Glow for Emergency Priority Intersection */}
              {isCorridorNode && (
                <circle
                  cx={inter.x}
                  cy={inter.y}
                  r={38}
                  fill="#10b981"
                  opacity={0.25}
                  filter="url(#corridor-glow)"
                  className="animate-pulse"
                />
              )}

              {/* Base Node Disc */}
              <circle
                cx={inter.x}
                cy={inter.y}
                r={26}
                fill={isCorridorNode ? '#064e3b' : isSelected ? '#0369a1' : '#1e293b'}
                stroke={isCorridorNode ? '#10b981' : isSelected ? '#38bdf8' : '#475569'}
                strokeWidth={isCorridorNode ? 2.5 : isSelected ? 2.5 : 1.5}
                filter="drop-shadow(0 4px 6px rgba(0,0,0,0.4))"
              />

              {/* Intersection ID Label */}
              <text
                x={inter.x}
                y={inter.y - 4}
                textAnchor="middle"
                dominantBaseline="central"
                fill={isCorridorNode ? '#6ee7b7' : '#f8fafc'}
                fontSize="12"
                fontWeight="800"
                className="font-mono tracking-wide"
              >
                {inter.id}
              </text>

              {/* Forced or QUBO Green Mode Indicator */}
              <text
                x={inter.x}
                y={inter.y + 9}
                textAnchor="middle"
                dominantBaseline="central"
                fill={inter.forcedGreen ? '#34d399' : '#94a3b8'}
                fontSize="8"
                fontWeight="600"
                className="font-mono uppercase"
              >
                {inter.forcedGreen ? 'PRIORITY' : 'AUTO'}
              </text>

              {/* Traffic Signal Lights Around Intersection Perimeter */}
              {inter.outgoingDirections.map((outId) => {
                const targetNode = intersections.get(outId);
                if (!targetNode) return null;

                const dx = targetNode.x - inter.x;
                const dy = targetNode.y - inter.y;
                const dist = Math.hypot(dx, dy) || 1;
                const lightRadius = 32; // position just outside node circle

                const lx = inter.x + (dx / dist) * lightRadius;
                const ly = inter.y + (dy / dist) * lightRadius;

                const isGreen = activeGreenDir === outId;

                return (
                  <g key={`${inter.id}->${outId}`}>
                    {/* Signal Housing */}
                    <circle
                      cx={lx}
                      cy={ly}
                      r={6}
                      fill="#020617"
                      stroke="#475569"
                      strokeWidth={1}
                    />
                    {/* Signal Bulb */}
                    <circle
                      cx={lx}
                      cy={ly}
                      r={4.5}
                      fill={isGreen ? '#22c55e' : '#ef4444'}
                      opacity={isGreen ? 1.0 : 0.4}
                      filter={isGreen ? 'drop-shadow(0 0 6px #22c55e)' : undefined}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      {/* Interactive Legend & Queue Jumping Status Overlay */}
      <div className="absolute top-3 left-3 bg-slate-950/85 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-800 text-xs flex flex-col gap-1.5 shadow-lg">
        <div className="flex items-center gap-2 font-semibold text-slate-200">
          <Navigation className="w-3.5 h-3.5 text-cyan-400" />
          <span>2×3 Network Engine (M2)</span>
        </div>
        <div className="flex items-center gap-4 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" />
            <span>Green Light</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 opacity-60" />
            <span>Red Light</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Emergency Corridor</span>
          </div>
        </div>
      </div>

      {/* Queue Jumping Mode HUD Badge */}
      <div className="absolute top-3 right-3 flex items-center gap-2">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold backdrop-blur-md shadow-lg transition-colors ${
            queueJumpingEnabled
              ? 'bg-amber-950/70 border-amber-500/50 text-amber-300'
              : 'bg-slate-900/80 border-slate-700 text-slate-400'
          }`}
        >
          <Zap className={`w-3.5 h-3.5 ${queueJumpingEnabled ? 'text-amber-400 animate-pulse' : 'text-slate-500'}`} />
          <span>
            Queue Jumping:{' '}
            <strong className={queueJumpingEnabled ? 'text-amber-200' : 'text-slate-300'}>
              {queueJumpingEnabled ? 'PREEMPTION ACTIVE' : 'FIFO ONLY'}
            </strong>
          </span>
        </div>
      </div>

      {/* Active Corridor Notice */}
      {constraints.active && (
        <div className="absolute bottom-3 left-3 bg-red-950/80 border border-red-500/60 px-3.5 py-2 rounded-xl text-xs text-red-200 flex items-center gap-2.5 shadow-xl backdrop-blur-md animate-pulse">
          <Siren className="w-4 h-4 text-red-400 animate-bounce" />
          <div>
            <span className="font-bold text-red-100">EMERGENCY CORRIDOR ENGAGED:</span>{' '}
            <span className="font-mono text-red-300">
              {constraints.vehicles.map((v) => `${v.type.toUpperCase()} [${v.route.join(' → ')}]`).join(', ')}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
