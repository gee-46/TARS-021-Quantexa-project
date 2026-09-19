import React from 'react';
import { ControllerType } from '../types/traffic';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Zap,
  Cpu,
  PlusCircle,
  Clock,
  Car,
  Activity,
} from 'lucide-react';

interface ControlBarProps {
  isRunning: boolean;
  onToggleRun: () => void;
  onStepTick: () => void;
  onReset: () => void;
  onSpawnDemand: () => void;
  tickSpeed: number;
  onChangeSpeed: (speed: number) => void;
  activeController: ControllerType;
  onChangeController: (c: ControllerType) => void;
  queueJumpingEnabled: boolean;
  onToggleQueueJumping: () => void;
  tickCount: number;
  activeVehiclesCount: number;
  completedTripsCount: number;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  isRunning,
  onToggleRun,
  onStepTick,
  onReset,
  onSpawnDemand,
  tickSpeed,
  onChangeSpeed,
  activeController,
  onChangeController,
  queueJumpingEnabled,
  onToggleQueueJumping,
  tickCount,
  activeVehiclesCount,
  completedTripsCount,
}) => {
  return (
    <div className="bg-slate-900/95 border border-slate-800/90 rounded-2xl p-4 shadow-xl backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
      {/* Simulation Controls: Play, Step, Reset, Demand */}
      <div className="flex items-center gap-2.5">
        <button
          id="btn-play-pause"
          onClick={onToggleRun}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-md active:scale-95 ${
            isRunning
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30'
              : 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-emerald-900/40'
          }`}
        >
          {isRunning ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
          <span>{isRunning ? 'Pause' : 'Play Sim'}</span>
        </button>

        <button
          id="btn-step-tick"
          onClick={onStepTick}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-medium rounded-xl border border-slate-700/80 transition-colors"
          title="Advance by 1 discrete tick"
        >
          <SkipForward className="w-4 h-4" />
          <span>Step</span>
        </button>

        <button
          id="btn-spawn-demand"
          onClick={onSpawnDemand}
          className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-800/90 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl border border-slate-700/70 transition-colors"
          title="Inject random traffic demand into network"
        >
          <PlusCircle className="w-4 h-4 text-cyan-400" />
          <span>+Traffic</span>
        </button>

        <button
          id="btn-reset"
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-800/80 hover:bg-rose-950/40 hover:text-rose-300 hover:border-rose-800/60 text-slate-400 text-sm font-medium rounded-xl border border-slate-700/60 transition-colors"
          title="Reset simulation to initial state"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>

        {/* Speed options */}
        <div className="flex items-center bg-slate-950/70 p-1 rounded-xl border border-slate-800 text-xs">
          {[0.5, 1, 2, 4].map((spd) => (
            <button
              key={spd}
              onClick={() => onChangeSpeed(spd)}
              className={`px-2.5 py-1.5 rounded-lg font-mono font-medium transition-colors ${
                tickSpeed === spd
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {spd}×
            </button>
          ))}
        </div>
      </div>

      {/* Center: Controller Selector */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span>Controller:</span>
        </div>
        <select
          id="select-controller"
          value={activeController}
          onChange={(e) => onChangeController(e.target.value as ControllerType)}
          className="bg-slate-950 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-500 cursor-pointer"
        >
          <option value="qaoa_xy">QAOA (p=3, XY-Mixer, Feasible)</option>
          <option value="qaoa_x">QAOA (p=3, X-Mixer, Penalty)</option>
          <option value="exact_qubo">Exact QUBO (Ground State)</option>
          <option value="simulated_annealing">Simulated Annealing QUBO</option>
          <option value="greedy_qubo">Greedy QUBO Optimizer</option>
          <option value="rule_based">Rule-Based (Longest Queue)</option>
          <option value="direct_corridor">Direct Corridor (Fixed + Override)</option>
          <option value="fixed_timing">Fixed Timing (Round-Robin)</option>
        </select>
      </div>

      {/* RIGHT: THE PROMINENT QUEUE JUMPING PREEMPTION TOGGLE */}
      <div className="flex items-center gap-3">
        <div
          onClick={onToggleQueueJumping}
          className={`flex items-center gap-3 px-3.5 py-2 rounded-xl border cursor-pointer select-none transition-all shadow-md ${
            queueJumpingEnabled
              ? 'bg-gradient-to-r from-amber-950/80 to-red-950/80 border-amber-500/60 shadow-amber-950/50 hover:border-amber-400'
              : 'bg-slate-950/80 border-slate-800 hover:border-slate-700 text-slate-400'
          }`}
          title="Toggle whether emergency vehicles jump directly to the head of road queues"
        >
          <div className="flex items-center gap-2">
            <Zap
              className={`w-4 h-4 transition-transform ${
                queueJumpingEnabled ? 'text-amber-400 scale-110' : 'text-slate-500'
              }`}
            />
            <div className="flex flex-col">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-200">
                Ambulance Queue Jump
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {queueJumpingEnabled ? '⚡ Preemption Enabled' : 'FIFO (Stuck Behind Cars)'}
              </span>
            </div>
          </div>

          {/* Toggle Switch Pill */}
          <div
            className={`w-10 h-5.5 rounded-full p-0.5 transition-colors relative ${
              queueJumpingEnabled ? 'bg-amber-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4.5 h-4.5 rounded-full bg-white transition-transform transform ${
                queueJumpingEnabled ? 'translate-x-4.5 shadow-sm' : 'translate-x-0'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Telemetry Metrics Pill */}
      <div className="w-full flex items-center justify-between pt-3 mt-1 border-t border-slate-800/80 text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Tick: <strong className="text-slate-100 font-bold">{tickCount}</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <Car className="w-3.5 h-3.5 text-emerald-400" />
            <span>Active Vehicles: <strong className="text-slate-100 font-bold">{activeVehiclesCount}</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-amber-400" />
            <span>Completed Trips: <strong className="text-slate-100 font-bold">{completedTripsCount}</strong></span>
          </div>
        </div>

        <div className="text-[11px] text-slate-500">
          M4 Live Operator Console • Engine M2 + Priority M3 + Optimizer M1
        </div>
      </div>
    </div>
  );
};
