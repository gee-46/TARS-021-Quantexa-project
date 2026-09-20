import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  getHealth,
  getScenarios,
  getNetwork,
  simulate,
  optimize,
  runEmergency,
} from '../services/api';
import { buildIntersections, buildRoads, emergencyRoutes } from '../services/networkGraph';

const TrafficContext = createContext(null);
const DEFAULT_SCENARIO = 'scenario_e_two_emergency_conflict';
const SEED = 42;

const fmtClock = (s) => {
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const sec = (s % 60).toString().padStart(2, '0');
  return `t=${m}:${sec}`;
};

export function TrafficProvider({ children }) {
  const [backend, setBackend] = useState({ status: 'connecting', info: null, error: null });
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO);
  const [network, setNetwork] = useState(null);
  const [baseline, setBaseline] = useState(null); // {plan, metrics}: fixed 30 s plan, no corridor
  const [current, setCurrent] = useState(null); // {plan, metrics}: what is displayed
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [emergencyResult, setEmergencyResult] = useState(null);
  const [isOptimized, setIsOptimized] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [emergencyCorridorActive, setEmergencyCorridorActive] = useState(false);
  const [emergencyBusy, setEmergencyBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedIntersectionId, setSelectedIntersectionId] = useState('I1');
  const [activeEvents, setActiveEvents] = useState([]);
  const [latestNotification, setLatestNotification] = useState(null);
  const [clock, setClock] = useState(0);
  // Read-only data for the live story screen: the same ambulance run with and without the corridor (existing /api/emergency).
  const [story, setStory] = useState({ status: 'none' });
  const [storyPhase, setStoryPhase] = useState(null);
  const storyToken = useRef(0);

  const pushEvent = useCallback((event) => {
    setActiveEvents((prev) => [
      { id: `EVT-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, timestamp: new Date().toLocaleTimeString(), ...event },
      ...prev.slice(0, 19),
    ]);
  }, []);

  const notify = useCallback((type, title, message) => setLatestNotification({ type, title, message }), []);

  const fail = useCallback(
    (err, title) => {
      const message = err?.message || 'Unknown error';
      if (err?.status === 0) setBackend((b) => ({ ...b, status: 'offline', error: message }));
      notify('ERROR', title, message);
      pushEvent({ title, location: 'QuantumFlow API', description: message, severity: 'ERROR' });
    },
    [notify, pushEvent],
  );

  // Model clock: loops through the simulated horizon (presentation only; drives the signal-phase display)
  const duration = network?.duration_seconds || 300;
  useEffect(() => {
    const timer = setInterval(() => setClock((c) => (c + 1) % duration), 1000);
    return () => clearInterval(timer);
  }, [duration]);

  const loadScenario = useCallback(
    async (id) => {
      setLoading(true);
      setLatestNotification(null);
      setOptimizationResult(null);
      setEmergencyResult(null);
      setIsOptimized(false);
      setEmergencyCorridorActive(false);
      try {
        const net = await getNetwork(id);
        const base = await simulate({ scenario: id, seed: SEED });
        setNetwork(net);
        setBaseline(base);
        setCurrent(base);
        storyToken.current += 1;
        const token = storyToken.current;
        if (net.ambulances.length > 0) {
          setStory({ status: 'loading' });
          runEmergency({ scenario: id, seed: SEED, plan: base.plan })
            .then((res) => storyToken.current === token && setStory({ status: 'ready', data: res }))
            .catch((e) => storyToken.current === token && setStory({ status: 'error', error: e.message }));
        } else {
          setStory({ status: 'none' });
        }
        setScenarioId(id);
        setSelectedIntersectionId(net.nodes[0].id);
        setBackend((b) => ({ ...b, status: 'online', error: null }));
        pushEvent({
          title: 'Scenario loaded',
          location: net.title,
          description: `${net.nodes.length} junctions, ${net.ambulances.length} emergency vehicle(s), fixed 30 s baseline simulated over ${net.duration_seconds} s (seed ${SEED}).`,
          severity: 'INFO',
        });
      } catch (err) {
        fail(err, 'Could not load scenario');
      } finally {
        setLoading(false);
      }
    },
    [fail, pushEvent],
  );

  // Boot: health -> scenario list -> default scenario
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [health, list] = await Promise.all([getHealth(), getScenarios()]);
        if (cancelled) return;
        setBackend({ status: 'online', info: health, error: null });
        setScenarios(list);
        await loadScenario(list.some((s) => s.id === DEFAULT_SCENARIO) ? DEFAULT_SCENARIO : list[0].id);
      } catch (err) {
        if (cancelled) return;
        setBackend({ status: 'offline', info: null, error: err.message });
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadScenario]);

  const handleRunOptimization = useCallback(async () => {
    setIsOptimizing(true);
    try {
      const res = await optimize({ scenario: scenarioId, seed: SEED });
      setOptimizationResult(res);
      notify('SUCCESS', 'Optimisation finished', res.verdict);
      pushEvent({ title: 'QUBO solved (QAOA / SA / Greedy)', location: `best: ${res.best_solver}`, description: res.verdict, severity: 'INFO' });
    } catch (err) {
      fail(err, 'Optimisation failed');
    } finally {
      setIsOptimizing(false);
    }
  }, [scenarioId, notify, pushEvent, fail]);

  const handleApplyOptimization = useCallback(() => {
    if (!optimizationResult) return;
    setCurrent(optimizationResult.optimized);
    setIsOptimized(true);
    setEmergencyCorridorActive(false);
    setEmergencyResult(null);
    notify('SUCCESS', 'Plan applied', 'Simulated results now use the solver-chosen signal plan.');
  }, [optimizationResult, notify]);

  const handleResetSignals = useCallback(() => {
    setCurrent(baseline);
    setIsOptimized(false);
    setEmergencyCorridorActive(false);
    setEmergencyResult(null);
    notify('INFO', 'Baseline restored', 'Fixed 30 s plan, no emergency corridor.');
  }, [baseline, notify]);

  const hasAmbulances = (network?.ambulances?.length || 0) > 0;

  const handleActivateCorridor = useCallback(async () => {
    if (!hasAmbulances) {
      notify('WARNING', 'No emergency vehicle', 'Pick a scenario that includes an ambulance (D, E, F or a Belagavi-inspired one).');
      return;
    }
    setEmergencyBusy(true);
    try {
      const res = await runEmergency({ scenario: scenarioId, seed: SEED, plan: current.plan });
      setEmergencyResult(res);
      setCurrent({ plan: res.plan, metrics: res.with_corridor });
      setEmergencyCorridorActive(true);
      const first = res.with_corridor.emergency_vehicle_results.map((v) => `${v.vehicle_id}: ${v.response_time ?? 'n/a'} s`).join(', ');
      notify('EMERGENCY', 'Emergency corridor simulated', `Ambulance response with corridor - ${first}.`);
      res.with_corridor.corridor_event_log
        .filter((e) => /Conflict|activated|preempt/i.test(e.message))
        .slice(0, 6)
        .forEach((e) => pushEvent({ title: e.event_type, location: `sim t=${e.timestamp}s`, description: e.message, severity: 'EMERGENCY' }));
    } catch (err) {
      fail(err, 'Emergency simulation failed');
    } finally {
      setEmergencyBusy(false);
    }
  }, [hasAmbulances, scenarioId, current, notify, pushEvent, fail]);

  const handleRestoreTraffic = useCallback(() => {
    if (emergencyResult) setCurrent({ plan: emergencyResult.plan, metrics: emergencyResult.without_corridor });
    setEmergencyCorridorActive(false);
    notify('INFO', 'Corridor off', 'Showing the same run without emergency preemption.');
  }, [emergencyResult, notify]);

  const dismissNotification = () => setLatestNotification(null);

  const intersections = useMemo(
    () =>
      buildIntersections({
        network,
        metrics: current?.metrics,
        plan: current?.plan,
        bestPlan: optimizationResult?.best_plan,
        clock,
      }),
    [network, current, optimizationResult, clock],
  );
  const roads = useMemo(() => buildRoads(network, intersections), [network, intersections]);
  const routes = useMemo(() => emergencyRoutes(network), [network]);
  const emergencyRoute = useMemo(() => [...new Set(routes.flatMap((r) => r.route))], [routes]);

  const selectedIntersection = intersections[selectedIntersectionId] || Object.values(intersections)[0] || null;

  const value = {
    // backend + scenario
    backend,
    scenarios,
    scenarioId,
    selectScenario: loadScenario,
    network,
    loading,
    seed: SEED,
    // data
    intersections,
    roads,
    metrics: current?.metrics || null,
    baselineMetrics: baseline?.metrics || null,
    currentPlan: current?.plan || null,
    baselinePlan: baseline?.plan || null,
    optimizationResult,
    emergencyResult,
    // flags
    isOptimized,
    isOptimizing,
    emergencyCorridorActive,
    emergencyBusy,
    hasAmbulances,
    // emergency routes (from the scenario's real ambulance configs)
    emergencyRoute,
    emergencyRoutes: routes,
    // selection & notifications
    selectedIntersectionId,
    setSelectedIntersectionId,
    selectedIntersection,
    activeEvents,
    latestNotification,
    dismissNotification,
    pushEvent,
    notify,
    // live story data + numeric model clock
    story,
    storyPhase,
    setStoryPhase,
    clock,
    // status
    simulationTime: fmtClock(clock),
    systemStatus: backend.status === 'online' ? 'ONLINE' : backend.status === 'offline' ? 'API OFFLINE' : 'CONNECTING',
    quantumEngineStatus: 'AER SIMULATOR',
    // actions
    handleRunOptimization,
    handleApplyOptimization,
    handleResetSignals,
    handleActivateCorridor,
    handleRestoreTraffic,
  };

  return <TrafficContext.Provider value={value}>{children}</TrafficContext.Provider>;
}

export function useTraffic() {
  const ctx = useContext(TrafficContext);
  if (!ctx) {
    throw new Error('useTraffic must be used within TrafficProvider');
  }
  return ctx;
}
