import React, { useState } from 'react';
import { Road, IntersectionId } from '../types/traffic';
import { AlertTriangle, Flame, Ban, CheckCircle2, Shuffle } from 'lucide-react';

interface HazardsPanelProps {
  roads: Map<string, Road>;
  onApplyAccident: (from: IntersectionId, to: IntersectionId) => void;
  onApplyCongestion: (from: IntersectionId, to: IntersectionId, factor: number) => void;
  onApplyClosure: (from: IntersectionId, to: IntersectionId) => void;
  onClearHazard: (from: IntersectionId, to: IntersectionId) => void;
  onClearAllHazards: () => void;
}

export const HazardsPanel: React.FC<HazardsPanelProps> = ({
  roads,
  onApplyAccident,
  onApplyCongestion,
  onApplyClosure,
  onClearHazard,
  onClearAllHazards,
}) => {
  const roadList = Array.from(roads.values());
  const [selectedRoadId, setSelectedRoadId] = useState<string>(roadList[0]?.id || 'I1->I2');
  const [congestionFactor, setCongestionFactor] = useState<number>(0.5);

  const activeHazards = roadList.filter((r) => r.status !== 'normal');

  const handleApply = (type: 'accident' | 'congestion' | 'closure') => {
    const road = roads.get(selectedRoadId);
    if (!road) return;

    if (type === 'accident') {
      onApplyAccident(road.from, road.to);
    } else if (type === 'congestion') {
      onApplyCongestion(road.from, road.to, congestionFactor);
    } else if (type === 'closure') {
      onApplyClosure(road.from, road.to);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-amber-950/70 border border-amber-500/50 text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
              Network Hazards & Event Injection (M2)
            </h2>
            <p className="text-xs text-slate-400">
              Simulate traffic incidents, capacity bottlenecks, and structural road closures
            </p>
          </div>
        </div>

        {activeHazards.length > 0 && (
          <button
            onClick={onClearAllHazards}
            className="px-3 py-1.5 bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-500/50 text-emerald-300 text-xs font-semibold rounded-xl transition-colors shadow-md flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Clear All Hazards ({activeHazards.length})</span>
          </button>
        )}
      </div>

      {/* Target Road Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-300">
            Select Road Segment:
          </label>
          <select
            value={selectedRoadId}
            onChange={(e) => setSelectedRoadId(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono font-semibold rounded-xl px-3.5 py-2.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            {roadList.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} [Capacity: {r.capacityPerTick} veh/tick | Queue: {r.vehicles.length} | Status: {r.status.toUpperCase()}]
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
            <span>Congestion Throughput Factor:</span>
            <span className="font-mono text-amber-400">{Math.round(congestionFactor * 100)}% Throughput</span>
          </label>
          <input
            type="range"
            min="0.2"
            max="0.8"
            step="0.1"
            value={congestionFactor}
            onChange={(e) => setCongestionFactor(parseFloat(e.target.value))}
            className="w-full accent-amber-500 cursor-pointer"
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <button
          onClick={() => handleApply('accident')}
          className="p-3 bg-red-950/40 hover:bg-red-900/60 border border-red-500/50 hover:border-red-400 text-red-200 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 shadow-md"
        >
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span>Inject Accident (Cap: 0)</span>
        </button>

        <button
          onClick={() => handleApply('congestion')}
          className="p-3 bg-amber-950/40 hover:bg-amber-900/60 border border-amber-500/50 hover:border-amber-400 text-amber-200 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 shadow-md"
        >
          <Flame className="w-4 h-4 text-amber-400" />
          <span>Apply Congestion</span>
        </button>

        <button
          onClick={() => handleApply('closure')}
          className="p-3 bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-300 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 shadow-md"
        >
          <Ban className="w-4 h-4 text-slate-400" />
          <span>Road Closure</span>
        </button>

        <button
          onClick={() => {
            const road = roads.get(selectedRoadId);
            if (road) onClearHazard(road.from, road.to);
          }}
          className="p-3 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-500/50 hover:border-emerald-400 text-emerald-200 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 shadow-md"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Restore Selected Road</span>
        </button>
      </div>

      {/* Active Hazards Table */}
      <div className="bg-slate-950/50 rounded-xl p-3.5 border border-slate-800">
        <div className="text-xs font-semibold text-slate-300 mb-2.5">
          Active Network Incidents: ({activeHazards.length})
        </div>

        {activeHazards.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500 italic">
            No incidents currently affecting the network. All roads operating at 100% nominal capacity.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {activeHazards.map((h) => (
              <div
                key={h.id}
                className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-mono font-bold text-slate-200">{h.id}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Status: <strong className={h.status === 'accident' ? 'text-red-400' : 'text-amber-400'}>{h.status.toUpperCase()}</strong>
                  </div>
                </div>

                <button
                  onClick={() => onClearHazard(h.from, h.to)}
                  className="px-2 py-1 bg-slate-800 hover:bg-emerald-900 text-slate-300 hover:text-emerald-200 rounded text-[11px] font-medium transition-colors"
                >
                  Clear
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
