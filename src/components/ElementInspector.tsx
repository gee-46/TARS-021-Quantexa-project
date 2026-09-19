import React from 'react';
import { Intersection, Road, Vehicle } from '../types/traffic';
import { X, Siren, Zap, AlertTriangle, CheckCircle2, Car } from 'lucide-react';

interface ElementInspectorProps {
  element: { type: 'intersection' | 'road'; id: string } | null;
  intersections: Map<string, Intersection>;
  roads: Map<string, Road>;
  onClose: () => void;
  onApplyAccident?: (from: string, to: string) => void;
  onApplyCongestion?: (from: string, to: string, factor: number) => void;
  onClearHazard?: (from: string, to: string) => void;
}

export const ElementInspector: React.FC<ElementInspectorProps> = ({
  element,
  intersections,
  roads,
  onClose,
  onApplyAccident,
  onApplyCongestion,
  onClearHazard,
}) => {
  if (!element) return null;

  if (element.type === 'intersection') {
    const inter = intersections.get(element.id);
    if (!inter) return null;

    return (
      <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-4 shadow-2xl backdrop-blur-md flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-cyan-500" />
            <span className="font-bold font-mono text-sm text-slate-100">
              Intersection {inter.id}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
            <span className="text-[10px] text-slate-400 block font-sans">Active Green Phase:</span>
            <span className="text-emerald-400 font-bold text-sm">
              {inter.forcedGreen ? `${inter.forcedGreen} (FORCED)` : inter.currentGreen ?? 'None'}
            </span>
          </div>
          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
            <span className="text-[10px] text-slate-400 block font-sans">Signal Control Mode:</span>
            <span className={inter.forcedGreen ? 'text-amber-400 font-bold' : 'text-slate-300'}>
              {inter.forcedGreen ? 'Corridor Override' : 'Optimizer / Cycle'}
            </span>
          </div>
        </div>

        <div className="text-xs">
          <span className="text-slate-400 font-semibold block mb-1">Outgoing Directions:</span>
          <div className="flex flex-wrap gap-1.5">
            {inter.outgoingDirections.map((dir) => (
              <span
                key={dir}
                className={`px-2.5 py-1 rounded-lg font-mono text-xs font-bold ${
                  (inter.forcedGreen ?? inter.currentGreen) === dir
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                → {dir}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Road Element
  const road = roads.get(element.id);
  if (!road) return null;

  return (
    <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-4 shadow-2xl backdrop-blur-md flex flex-col gap-3 max-w-sm">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-500" />
          <span className="font-bold font-mono text-sm text-slate-100">
            Road {road.id}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
        <div className="bg-slate-950 p-2 rounded-xl border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-sans">Queue:</span>
          <span className="text-cyan-300 font-bold text-sm">{road.vehicles.length} veh</span>
        </div>
        <div className="bg-slate-950 p-2 rounded-xl border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-sans">Capacity:</span>
          <span className="text-emerald-400 font-bold text-sm">{road.capacityPerTick}/tick</span>
        </div>
        <div className="bg-slate-950 p-2 rounded-xl border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-sans">Status:</span>
          <span className={`font-bold text-xs uppercase ${road.status === 'normal' ? 'text-emerald-400' : 'text-red-400'}`}>
            {road.status}
          </span>
        </div>
      </div>

      {/* Vehicles in Queue with explicit Queue-Jumping preemption badges */}
      <div>
        <div className="text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
          <span>Queued Vehicles (Front → Back):</span>
          <span className="text-[10px] font-mono text-slate-400">{road.vehicles.length} total</span>
        </div>

        {road.vehicles.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-2 bg-slate-950 rounded-lg text-center">
            Queue empty
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto pr-1">
            {road.vehicles.map((v, idx) => (
              <div
                key={v.id}
                className={`p-2 rounded-lg text-xs font-mono flex items-center justify-between ${
                  v.type !== 'normal'
                    ? 'bg-red-950/40 border border-red-500/40 text-red-200'
                    : 'bg-slate-950 border border-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-slate-500 font-bold">#{idx + 1}</span>
                  {v.type !== 'normal' ? (
                    <Siren className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                  ) : (
                    <Car className="w-3.5 h-3.5 text-slate-500" />
                  )}
                  <span className="font-bold">{v.id}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {v.queueJumpedCount > 0 && idx === 0 && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-bold">
                      ⚡ JUMPED
                    </span>
                  )}
                  <span className="text-[10px] text-slate-400">Wait: {v.totalWaitTime}t</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Hazard Actions */}
      <div className="flex items-center gap-1.5 pt-1">
        {road.status === 'normal' ? (
          <>
            <button
              onClick={() => onApplyAccident && onApplyAccident(road.from, road.to)}
              className="flex-1 py-1.5 bg-red-950/50 hover:bg-red-900/60 border border-red-500/40 text-red-300 text-[11px] font-bold rounded-lg transition-colors"
            >
              Set Accident
            </button>
            <button
              onClick={() => onApplyCongestion && onApplyCongestion(road.from, road.to, 0.5)}
              className="flex-1 py-1.5 bg-amber-950/50 hover:bg-amber-900/60 border border-amber-500/40 text-amber-300 text-[11px] font-bold rounded-lg transition-colors"
            >
              Congest 50%
            </button>
          </>
        ) : (
          <button
            onClick={() => onClearHazard && onClearHazard(road.from, road.to)}
            className="w-full py-1.5 bg-emerald-950/50 hover:bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 text-[11px] font-bold rounded-lg transition-colors"
          >
            Clear Incident
          </button>
        )}
      </div>
    </div>
  );
};
