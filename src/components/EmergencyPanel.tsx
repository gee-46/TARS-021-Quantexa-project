import React, { useState } from 'react';
import { VehicleType, IntersectionId, EmergencyConstraints, Vehicle } from '../types/traffic';
import { Siren, Flame, Shield, ArrowRight, Zap, CheckCircle2, History, AlertCircle } from 'lucide-react';

interface EmergencyPanelProps {
  onDispatchVehicle: (type: VehicleType, route: IntersectionId[]) => void;
  constraints: EmergencyConstraints;
  activeEmergencyVehicles: Vehicle[];
  queueJumpingEnabled: boolean;
  onToggleQueueJumping: () => void;
  tripHistory: { id: string; transitTicks: number; queueJumps: number; queueJumping: boolean }[];
  onClearCorridors: () => void;
}

export const EmergencyPanel: React.FC<EmergencyPanelProps> = ({
  onDispatchVehicle,
  constraints,
  activeEmergencyVehicles,
  queueJumpingEnabled,
  onToggleQueueJumping,
  tripHistory,
  onClearCorridors,
}) => {
  const [selectedType, setSelectedType] = useState<VehicleType>('ambulance');
  const [selectedPreset, setSelectedPreset] = useState<string>('mvp');
  const [startNode, setStartNode] = useState<IntersectionId>('I1');
  const [endNode, setEndNode] = useState<IntersectionId>('I6');

  // Predefined corridors matching spec
  const presets: Record<string, { label: string; route: IntersectionId[]; description: string }> = {
    mvp: {
      label: 'MVP Corridor (Spec Worked Example)',
      route: ['I1', 'I2', 'I4'],
      description: 'The standard 2-hop baseline corridor tested in demo_integration.py',
    },
    long_diagonal: {
      label: 'Express Cross-Grid Corridor',
      route: ['I1', 'I2', 'I3', 'I6'],
      description: '3-hop route traversing from top-left to bottom-right through I2 & I3',
    },
    arterial: {
      label: 'Arterial Central Traverse',
      route: ['I4', 'I5', 'I2', 'I3'],
      description: 'Ascends central spine from I5 to I2 and cuts east',
    },
  };

  const handleDispatch = () => {
    let route: IntersectionId[];
    if (selectedPreset === 'custom') {
      route = [startNode, endNode]; // will be solved via shortest path in engine
    } else {
      route = presets[selectedPreset].route;
    }
    onDispatchVehicle(selectedType, route);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-red-950/70 border border-red-500/50 text-red-400">
            <Siren className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
              Emergency Corridor & Preemption (M3)
            </h2>
            <p className="text-xs text-slate-400">
              Priority signal green-wave and dynamic queue jumping
            </p>
          </div>
        </div>

        {/* Clear / Reset Active Corridor */}
        {constraints.active && (
          <button
            onClick={onClearCorridors}
            className="px-3 py-1.5 bg-red-950/80 hover:bg-red-900 border border-red-600/60 text-red-200 text-xs font-semibold rounded-xl transition-colors shadow-md"
          >
            Clear Active Corridors
          </button>
        )}
      </div>

      {/* 1. VEHICLE DISPATCH SELECTOR */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Ambulance */}
        <button
          onClick={() => setSelectedType('ambulance')}
          className={`p-3.5 rounded-xl border flex items-center gap-3 transition-all ${
            selectedType === 'ambulance'
              ? 'bg-red-950/60 border-red-500 text-red-200 shadow-lg shadow-red-950/40 ring-1 ring-red-500'
              : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700'
          }`}
        >
          <div className="p-2 rounded-lg bg-red-500/20 text-red-400">
            <Siren className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-slate-100">Ambulance</div>
            <div className="text-[11px] font-mono text-red-400">Priority: 100 (Max)</div>
          </div>
        </button>

        {/* Fire Truck */}
        <button
          onClick={() => setSelectedType('fire_truck')}
          className={`p-3.5 rounded-xl border flex items-center gap-3 transition-all ${
            selectedType === 'fire_truck'
              ? 'bg-orange-950/60 border-orange-500 text-orange-200 shadow-lg shadow-orange-950/40 ring-1 ring-orange-500'
              : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700'
          }`}
        >
          <div className="p-2 rounded-lg bg-orange-500/20 text-orange-400">
            <Flame className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-slate-100">Fire Engine</div>
            <div className="text-[11px] font-mono text-orange-400">Priority: 80</div>
          </div>
        </button>

        {/* Police Cruiser */}
        <button
          onClick={() => setSelectedType('police')}
          className={`p-3.5 rounded-xl border flex items-center gap-3 transition-all ${
            selectedType === 'police'
              ? 'bg-blue-950/60 border-blue-500 text-blue-200 shadow-lg shadow-blue-950/40 ring-1 ring-blue-500'
              : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700'
          }`}
        >
          <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
            <Shield className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-slate-100">Police Cruiser</div>
            <div className="text-[11px] font-mono text-blue-400">Priority: 60</div>
          </div>
        </button>
      </div>

      {/* 2. CORRIDOR ROUTE PRESETS */}
      <div className="flex flex-col gap-2">
        <label className="text-xs font-semibold text-slate-300">
          Select Emergency Route Corridor:
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {Object.entries(presets).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => setSelectedPreset(key)}
              className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                selectedPreset === key
                  ? 'bg-cyan-950/50 border-cyan-500 text-slate-100 shadow-md ring-1 ring-cyan-500'
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="font-semibold text-xs text-slate-200 mb-1">{preset.label}</div>
              <div className="font-mono text-xs font-bold text-emerald-400 flex items-center gap-1">
                {preset.route.join(' → ')}
              </div>
              <div className="text-[10px] text-slate-500 mt-1.5 leading-relaxed">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 3. DISPATCH ACTION & QUEUE JUMPING IMPACT */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/90 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${queueJumpingEnabled ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-500'}`}>
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
              <span>Queue Jumping Preemption:</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${queueJumpingEnabled ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-400'}`}>
                {queueJumpingEnabled ? 'ACTIVE (PREEMPTION)' : 'OFF (FIFO WAIT)'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 max-w-xl">
              {queueJumpingEnabled
                ? '⚡ Emergency vehicles bypass ordinary cars and jump straight to index 0 of every road queue, guaranteeing immediate transit on green!'
                : '⚠️ FIFO mode: Emergency vehicles are held behind queued normal cars, even if the signal light is forced green.'}
            </p>
          </div>
        </div>

        <button
          onClick={handleDispatch}
          className="w-full md:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-red-950/60 active:scale-95 transition-all"
        >
          <Siren className="w-4 h-4 animate-bounce" />
          <span>Dispatch Emergency Vehicle</span>
        </button>
      </div>

      {/* 4. ACTIVE EMERGENCY VEHICLES & HISTORICAL COMPARISON */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {/* Active Emergency Vehicles */}
        <div className="bg-slate-950/40 rounded-xl p-3.5 border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">Active In-Transit:</span>
            <span className="text-xs font-mono text-cyan-400">{activeEmergencyVehicles.length} active</span>
          </div>

          {activeEmergencyVehicles.length === 0 ? (
            <div className="py-5 text-center text-xs text-slate-500 italic">
              No emergency vehicles currently on the network.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {activeEmergencyVehicles.map((veh) => {
                const currentFrom = veh.route[veh.currentHopIndex];
                const currentTo = veh.route[veh.currentHopIndex + 1] ?? 'Destination';
                return (
                  <div
                    key={veh.id}
                    className="p-2.5 rounded-lg bg-red-950/30 border border-red-500/30 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <Siren className="w-4 h-4 text-red-400 animate-pulse" />
                      <div>
                        <span className="font-bold text-red-200">{veh.id}</span>
                        <span className="text-slate-400 text-[11px] ml-2">
                          Hop {veh.currentHopIndex + 1}/{veh.route.length - 1} ({currentFrom} → {currentTo})
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-right">
                      {veh.queueJumpedCount > 0 && (
                        <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px] font-bold">
                          ⚡ Jumped {veh.queueJumpedCount} cars
                        </span>
                      )}
                      <span className="font-mono text-slate-300 text-[11px]">
                        Wait: {veh.totalWaitTime}t
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Historical Transit Ticks Comparison */}
        <div className="bg-slate-950/40 rounded-xl p-3.5 border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-cyan-400" />
              <span>Recent Ambulance Arrivals:</span>
            </span>
            <span className="text-[11px] text-slate-400">Target: ~3-4 ticks</span>
          </div>

          {tripHistory.length === 0 ? (
            <div className="py-5 text-center text-xs text-slate-500 italic">
              Dispatched ambulances will log transit times and jump metrics here.
            </div>
          ) : (
            <div className="flex flex-col gap-2 max-h-36 overflow-y-auto">
              {tripHistory.slice(-4).reverse().map((trip, idx) => (
                <div
                  key={`${trip.id}-${idx}`}
                  className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-mono font-bold text-slate-200">{trip.id}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${trip.queueJumping ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'}`}>
                      {trip.queueJumping ? 'Queue Jump ON' : 'FIFO'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-emerald-400 font-bold">{trip.transitTicks} ticks</span>
                    {trip.queueJumps > 0 && (
                      <span className="text-amber-400 text-[11px]">({trip.queueJumps} bypassed)</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
