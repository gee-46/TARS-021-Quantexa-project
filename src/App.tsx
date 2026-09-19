import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  TrafficNetwork,
  TrafficSimulator,
  EmergencyManager,
} from './engine/trafficEngine';
import {
  ControllerType,
  IntersectionId,
  VehicleType,
  SolverResult,
  EmergencyConstraints,
  BenchmarkRow,
} from './types/traffic';
import { QUBOBuilder, QUBOProblem } from './optimizer/qubo';
import {
  ExactSolver,
  QAOASolver,
  SimulatedAnnealingSolver,
  GreedySolver,
  getRuleBasedPlan,
} from './optimizer/solvers';
import { runBenchmarkComparison } from './optimizer/benchmark';

import { NetworkCanvas } from './components/NetworkCanvas';
import { ControlBar } from './components/ControlBar';
import { EmergencyPanel } from './components/EmergencyPanel';
import { HazardsPanel } from './components/HazardsPanel';
import { BenchmarkView } from './components/BenchmarkView';
import { QuantumInspector } from './components/QuantumInspector';
import { ElementInspector } from './components/ElementInspector';
import { LogDrawer } from './components/LogDrawer';

import {
  Activity,
  Award,
  Atom,
  AlertTriangle,
  Siren,
  Sparkles,
  Zap,
  Info,
  Radio,
} from 'lucide-react';

export default function App() {
  // Engine & Simulator Instances
  const [network] = useState<TrafficNetwork>(() => new TrafficNetwork());
  const [emergencyMgr] = useState<EmergencyManager>(() => new EmergencyManager());
  const [simulator] = useState<TrafficSimulator>(
    () => new TrafficSimulator(network, emergencyMgr)
  );

  // Solvers
  const quboBuilder = useMemo(() => new QUBOBuilder(), []);
  const exactSolver = useMemo(() => new ExactSolver(), []);
  const qaoaXYSolver = useMemo(() => new QAOASolver({ p: 3, mixer: 'xy' }), []);
  const qaoaXSolver = useMemo(() => new QAOASolver({ p: 3, mixer: 'x' }), []);
  const saSolver = useMemo(() => new SimulatedAnnealingSolver(), []);
  const greedySolver = useMemo(() => new GreedySolver(), []);

  // Simulation State
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [tickSpeed, setTickSpeed] = useState<number>(1);
  const [activeController, setActiveController] = useState<ControllerType>('qaoa_xy');
  const [queueJumpingEnabled, setQueueJumpingEnabled] = useState<boolean>(true);

  // Active View Tab
  const [activeTab, setActiveTab] = useState<
    'network' | 'emergency' | 'hazards' | 'benchmark' | 'quantum'
  >('network');

  // Inspector Selection
  const [selectedElement, setSelectedElement] = useState<{
    type: 'intersection' | 'road';
    id: string;
  } | null>(null);

  // State Triggers for React Rendering
  const [simTick, setSimTick] = useState<number>(0);
  const [lastProblem, setLastProblem] = useState<QUBOProblem | null>(null);
  const [lastSolverResult, setLastSolverResult] = useState<SolverResult | null>(null);

  // Benchmark Cache
  const [benchmarkRows, setBenchmarkRows] = useState<BenchmarkRow[]>([]);

  // Keep simulator queueJumping in sync
  useEffect(() => {
    simulator.queueJumpingEnabled = queueJumpingEnabled;
  }, [queueJumpingEnabled, simulator]);

  // Initial population with some sample vehicles
  useEffect(() => {
    simulator.spawnRandomBackgroundDemand(4);
    // Initial solve
    runOptimizationStep();
    setSimTick(simulator.tickCount);
    // Pre-calculate initial benchmark
    const initialBench = runBenchmarkComparison({ queueJumping: true });
    setBenchmarkRows(initialBench);
  }, []);

  // Optimization step (called every epoch)
  const runOptimizationStep = () => {
    const state = simulator.getNetworkState();
    const constraints = emergencyMgr.getConstraints();

    if (activeController === 'fixed_timing') {
      // Normal simulator round-robin
      return;
    }

    if (activeController === 'direct_corridor') {
      if (constraints.active) {
        const plan: Record<IntersectionId, IntersectionId> = {};
        for (const [u, v] of constraints.corridor_hops) {
          plan[u] = v;
        }
        simulator.applySignalPlan(plan);
      } else {
        simulator.clearForcedGreens();
      }
      return;
    }

    if (activeController === 'rule_based') {
      const plan = getRuleBasedPlan(state);
      if (constraints.active) {
        for (const [u, v] of constraints.corridor_hops) {
          plan[u] = v;
        }
      }
      simulator.applySignalPlan(plan);
      return;
    }

    // QUBO based controllers
    const problem = quboBuilder.build(state, constraints);
    setLastProblem(problem);

    let res: SolverResult;
    if (activeController === 'qaoa_xy') {
      res = qaoaXYSolver.solve(problem);
    } else if (activeController === 'qaoa_x') {
      res = qaoaXSolver.solve(problem);
    } else if (activeController === 'exact_qubo') {
      res = exactSolver.solve(problem);
    } else if (activeController === 'simulated_annealing') {
      res = saSolver.solve(problem);
    } else {
      res = greedySolver.solve(problem);
    }

    setLastSolverResult(res);
    simulator.applySignalPlan(res.plan);
  };

  // Step function
  const stepTick = () => {
    // Re-solve every 2 ticks (control epoch)
    if (simulator.tickCount % 2 === 0) {
      runOptimizationStep();
    }
    simulator.tick();
    setSimTick(simulator.tickCount);
  };

  // Simulation Clock Loop
  useEffect(() => {
    if (!isRunning) return;

    const intervalMs = Math.max(150, 750 / tickSpeed);
    const timer = setInterval(() => {
      stepTick();
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isRunning, tickSpeed, activeController, queueJumpingEnabled]);

  // Handler: Dispatch Emergency Vehicle
  const handleDispatch = (type: VehicleType, route: IntersectionId[]) => {
    const fullRoute =
      route.length === 2 ? network.shortestRoute(route[0], route[1]) : route;
    emergencyMgr.reportVehicle(type, fullRoute, simulator.tickCount);
    simulator.spawnVehicle(fullRoute, type);
    // Immediately solve for newly activated corridor
    runOptimizationStep();
    setSimTick(simulator.tickCount);
  };

  // Handler: Reset Simulator
  const handleReset = () => {
    setIsRunning(false);
    network.buildDefaultGrid();
    emergencyMgr.events.clear();
    simulator.vehicles.clear();
    simulator.completedTrips = 0;
    simulator.totalWaitTime = 0;
    simulator.tickCount = 0;
    simulator.totalFuelWastedLiters = 0;
    simulator.totalCO2EmissionsKg = 0;
    simulator.totalQueueJumps = 0;
    simulator.ambulanceTripHistory = [];
    simulator.logs = [];
    simulator.spawnRandomBackgroundDemand(4);
    runOptimizationStep();
    setSimTick(0);
  };

  const constraints = emergencyMgr.getConstraints();
  const activeEmergencyVehicles = Array.from(simulator.vehicles.values()).filter(
    (v) => v.type !== 'normal'
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-cyan-500/20 selection:text-cyan-300">
      {/* Top Banner & Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
              <Atom className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-extrabold tracking-tight text-white font-['Plus_Jakarta_Sans',sans-serif]">
                  Quantum Traffic Optimizer <span className="text-cyan-400 font-mono text-xs px-2 py-0.5 rounded-md bg-cyan-950/80 border border-cyan-500/40">M4 Console</span>
                </h1>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                  <Radio className="w-2.5 h-2.5 text-emerald-400 animate-pulse" />
                  ONLINE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                End-to-End M1 (QUBO/QAOA) + M2 (Network Engine) + M3 (Emergency & Queue Jumping)
              </p>
            </div>
          </div>

          {/* Navigation View Tabs */}
          <div className="flex items-center bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('network')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all ${
                activeTab === 'network'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Live Simulation</span>
            </button>

            <button
              onClick={() => setActiveTab('emergency')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all ${
                activeTab === 'emergency'
                  ? 'bg-red-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Siren className="w-3.5 h-3.5" />
              <span>Emergency (M3)</span>
              {constraints.active && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping ml-0.5" />
              )}
            </button>

            <button
              onClick={() => setActiveTab('hazards')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all ${
                activeTab === 'hazards'
                  ? 'bg-amber-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Hazards (M2)</span>
            </button>

            <button
              onClick={() => setActiveTab('benchmark')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all ${
                activeTab === 'benchmark'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Award className="w-3.5 h-3.5" />
              <span>Benchmark & Eco</span>
            </button>

            <button
              onClick={() => setActiveTab('quantum')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all ${
                activeTab === 'quantum'
                  ? 'bg-purple-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Atom className="w-3.5 h-3.5" />
              <span>QUBO & QAOA (M1)</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col gap-5">
        {/* Simulation Control Bar */}
        <ControlBar
          isRunning={isRunning}
          onToggleRun={() => setIsRunning(!isRunning)}
          onStepTick={stepTick}
          onReset={handleReset}
          onSpawnDemand={() => {
            simulator.spawnRandomBackgroundDemand(3);
            setSimTick(simulator.tickCount);
          }}
          tickSpeed={tickSpeed}
          onChangeSpeed={setTickSpeed}
          activeController={activeController}
          onChangeController={(c) => {
            setActiveController(c);
            setTimeout(runOptimizationStep, 10);
          }}
          queueJumpingEnabled={queueJumpingEnabled}
          onToggleQueueJumping={() => setQueueJumpingEnabled(!queueJumpingEnabled)}
          tickCount={simulator.tickCount}
          activeVehiclesCount={simulator.vehicles.size}
          completedTripsCount={simulator.completedTrips}
        />

        {/* Tab 1: Live Simulation View (Canvas + Quick Controls) */}
        {activeTab === 'network' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left: 2D Grid Canvas & Element Inspector */}
            <div className="lg:col-span-8 flex flex-col gap-4">
              <NetworkCanvas
                intersections={network.intersections}
                roads={network.roads}
                vehicles={simulator.vehicles}
                constraints={constraints}
                queueJumpingEnabled={queueJumpingEnabled}
                selectedElement={selectedElement}
                onSelectElement={setSelectedElement}
              />

              {/* Clicked Element Inspector Card */}
              {selectedElement && (
                <ElementInspector
                  element={selectedElement}
                  intersections={network.intersections}
                  roads={network.roads}
                  onClose={() => setSelectedElement(null)}
                  onApplyAccident={(u, v) => {
                    simulator.applyAccident(u, v);
                    setSimTick(simulator.tickCount);
                  }}
                  onApplyCongestion={(u, v, f) => {
                    simulator.applyCongestion(u, v, f);
                    setSimTick(simulator.tickCount);
                  }}
                  onClearHazard={(u, v) => {
                    simulator.clearHazard(u, v);
                    setSimTick(simulator.tickCount);
                  }}
                />
              )}
            </div>

            {/* Right: Real-time Emergency & Queue Jump Quick Station */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              {/* Ambulance Queue Preemption Spotlight Box */}
              <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-950/70 via-slate-900 to-red-950/60 border border-amber-500/50 shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-300">
                      <Zap className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-200">
                      Ambulance Queue Preemption
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                      queueJumpingEnabled
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {queueJumpingEnabled ? 'ACTIVE' : 'FIFO'}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {queueJumpingEnabled
                    ? '⚡ Emergency vehicles overtake normal vehicles and jump straight to the head of the queue, clearing the green wave with zero bottleneck delay!'
                    : '⚠️ Standard FIFO queue: Ambulances are trapped behind normal cars even when the traffic signal turns green.'}
                </p>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                  <div className="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-[10px] font-sans text-slate-400 block">Queue Jumps:</span>
                    <span className="text-amber-300 font-bold text-base">
                      {simulator.totalQueueJumps}
                    </span>
                  </div>
                  <div className="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-[10px] font-sans text-slate-400 block">Last Transit:</span>
                    <span className="text-emerald-400 font-bold text-base">
                      {simulator.lastAmbulanceTransitTicks !== null
                        ? `${simulator.lastAmbulanceTransitTicks} ticks`
                        : 'Waiting'}
                    </span>
                  </div>
                </div>

                {/* Quick 1-Click Ambulance Dispatch */}
                <button
                  onClick={() => handleDispatch('ambulance', ['I1', 'I2', 'I4'])}
                  className="w-full py-2.5 px-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-red-950/50 active:scale-95 transition-all"
                >
                  <Siren className="w-4 h-4 animate-bounce" />
                  <span>Dispatch MVP Ambulance (I1→I2→I4)</span>
                </button>
              </div>

              {/* Environmental Real-Time Tracker Card */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl flex flex-col gap-2.5 text-xs">
                <div className="flex items-center justify-between text-slate-300 font-semibold border-b border-slate-800 pb-2">
                  <span>Environmental Metrics (Live)</span>
                  <span className="text-[10px] font-mono text-emerald-400">Idle Emissions</span>
                </div>
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400">Fuel Consumed (Idle):</span>
                  <span className="text-amber-300 font-bold">
                    {Math.round(simulator.totalFuelWastedLiters * 100) / 100} L
                  </span>
                </div>
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400">CO2 Generated:</span>
                  <span className="text-emerald-300 font-bold">
                    {Math.round(simulator.totalCO2EmissionsKg * 100) / 100} kg
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 pt-1 leading-relaxed">
                  Calculated from vehicles waiting at red lights vs smoothed green flow.
                </div>
              </div>

              {/* Active Corridor Card */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl flex flex-col gap-2 text-xs">
                <div className="flex items-center justify-between font-semibold text-slate-300 border-b border-slate-800 pb-2">
                  <span>Active Emergency Vehicles</span>
                  <span className="text-[10px] font-mono text-cyan-400">
                    {activeEmergencyVehicles.length} on road
                  </span>
                </div>

                {activeEmergencyVehicles.length === 0 ? (
                  <div className="text-slate-500 italic py-2 text-center">
                    No emergency vehicles active
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {activeEmergencyVehicles.map((v) => (
                      <div
                        key={v.id}
                        className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <Siren className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                          <span className="font-mono font-bold text-slate-200">{v.id}</span>
                        </div>
                        <span className="font-mono text-amber-300 text-[11px]">
                          Hop {v.currentHopIndex + 1}/{v.route.length - 1}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Full Emergency Command (M3) */}
        {activeTab === 'emergency' && (
          <EmergencyPanel
            onDispatchVehicle={handleDispatch}
            constraints={constraints}
            activeEmergencyVehicles={activeEmergencyVehicles}
            queueJumpingEnabled={queueJumpingEnabled}
            onToggleQueueJumping={() => setQueueJumpingEnabled(!queueJumpingEnabled)}
            tripHistory={simulator.ambulanceTripHistory}
            onClearCorridors={() => {
              for (const id of emergencyMgr.events.keys()) {
                emergencyMgr.clear(id);
              }
              simulator.clearForcedGreens();
              runOptimizationStep();
              setSimTick(simulator.tickCount);
            }}
          />
        )}

        {/* Tab 3: Hazard & Event Injection (M2) */}
        {activeTab === 'hazards' && (
          <HazardsPanel
            roads={network.roads}
            onApplyAccident={(u, v) => {
              simulator.applyAccident(u, v);
              setSimTick(simulator.tickCount);
            }}
            onApplyCongestion={(u, v, f) => {
              simulator.applyCongestion(u, v, f);
              setSimTick(simulator.tickCount);
            }}
            onApplyClosure={(u, v) => {
              simulator.applyClosure(u, v);
              setSimTick(simulator.tickCount);
            }}
            onClearHazard={(u, v) => {
              simulator.clearHazard(u, v);
              setSimTick(simulator.tickCount);
            }}
            onClearAllHazards={() => {
              for (const r of network.roads.values()) {
                simulator.clearHazard(r.from, r.to);
              }
              setSimTick(simulator.tickCount);
            }}
          />
        )}

        {/* Tab 4: Multi-Solver Benchmark & Environmental Metrics */}
        {activeTab === 'benchmark' && (
          <BenchmarkView
            initialRows={benchmarkRows}
            currentQueueJumping={queueJumpingEnabled}
          />
        )}

        {/* Tab 5: QUBO & QAOA Quantum State Inspector (M1) */}
        {activeTab === 'quantum' && (
          <QuantumInspector
            problem={lastProblem}
            lastSolverResult={lastSolverResult}
          />
        )}

        {/* Activity & Dispatch Log Drawer (Always accessible at bottom) */}
        <LogDrawer logs={simulator.logs} />
      </main>
    </div>
  );
}
