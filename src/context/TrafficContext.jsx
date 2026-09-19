import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getTrafficState,
  runQuantumOptimization,
  applyOptimizedSignals,
  triggerTrafficEvent,
  activateEmergencyCorridor,
  restoreTraffic,
  BASELINE_METRICS,
  OPTIMIZED_METRICS,
} from '../services/api';
import { INITIAL_INTERSECTIONS, INITIAL_ROADS, EMERGENCY_ROUTE } from '../services/networkGraph';

const TrafficContext = createContext(null);

export function TrafficProvider({ children }) {
  const [intersections, setIntersections] = useState(INITIAL_INTERSECTIONS);
  const [roads, setRoads] = useState(INITIAL_ROADS);
  const [metrics, setMetrics] = useState(BASELINE_METRICS);
  const [isOptimized, setIsOptimized] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [emergencyCorridorActive, setEmergencyCorridorActive] = useState(false);
  const [selectedIntersectionId, setSelectedIntersectionId] = useState('I1');
  const [activeEvents, setActiveEvents] = useState([
    {
      id: 'EVT-INIT',
      title: 'Traffic System Synchronized',
      location: '6 Connected Hubs Active',
      timestamp: '08:00:00',
      severity: 'INFO',
      description: 'NetworkX topology and telemetry streaming active.',
    },
  ]);
  const [latestNotification, setLatestNotification] = useState(null);
  const [simTimeSeconds, setSimTimeSeconds] = useState(872); // T+00:14:32

  // Simulation Clock Tick
  useEffect(() => {
    const timer = setInterval(() => {
      setSimTimeSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatSimTime = (totalSec) => {
    const hrs = Math.floor(totalSec / 3600).toString().padStart(2, '0');
    const mins = Math.floor((totalSec % 3600) / 60).toString().padStart(2, '0');
    const secs = (totalSec % 60).toString().padStart(2, '0');
    return `T+${hrs}:${mins}:${secs}`;
  };

  // Run QAOA Optimization
  const handleRunOptimization = useCallback(async () => {
    setIsOptimizing(true);
    try {
      const res = await runQuantumOptimization({ intersections, roads, metrics });
      setOptimizationResult(res);
      setLatestNotification({
        type: 'SUCCESS',
        title: 'Quantum Optimization Converged',
        message: 'QAOA generated optimal signal timing schedule (Cost: -1842.38)',
      });
      return res;
    } catch (err) {
      console.error('Optimization error:', err);
    } finally {
      setIsOptimizing(false);
    }
  }, [intersections, roads, metrics]);

  // Apply QAOA Solution
  const handleApplyOptimization = useCallback(async () => {
    if (!optimizationResult) return;
    const applied = await applyOptimizedSignals(optimizationResult);
    setIntersections(applied.intersections);
    setMetrics(applied.metrics);
    setIsOptimized(true);
    setLatestNotification({
      type: 'SUCCESS',
      title: 'Signals Applied',
      message: 'Adaptive timing deployed across all 6 intersections. Wait time reduced by 38%.',
    });
  }, [optimizationResult]);

  // Reset Signals
  const handleResetSignals = useCallback(async () => {
    const res = await restoreTraffic(INITIAL_INTERSECTIONS);
    setIntersections(res.intersections);
    setRoads(INITIAL_ROADS);
    setMetrics(BASELINE_METRICS);
    setIsOptimized(false);
    setEmergencyCorridorActive(false);
    setOptimizationResult(null);
    setLatestNotification({
      type: 'INFO',
      title: 'Signals Reset to Classical Baseline',
      message: 'Fixed signal timing baseline restored.',
    });
  }, []);

  // Trigger Traffic Event
  const handleTriggerEvent = useCallback(async (eventType) => {
    const result = await triggerTrafficEvent(eventType, { intersections, roads, metrics });
    setIntersections(result.intersections);
    setRoads(result.roads);
    setMetrics(result.metrics);
    if (result.event && result.event.title) {
      setActiveEvents((prev) => [
        { ...result.event, id: `EVT-${Date.now()}` },
        ...prev.slice(0, 8),
      ]);
      setLatestNotification({
        type: result.event.severity === 'CRITICAL' ? 'ERROR' : 'WARNING',
        title: result.event.title,
        message: `${result.event.location} - ${result.event.description}`,
      });
    }
  }, [intersections, roads, metrics]);

  // Activate Emergency Corridor
  const handleActivateCorridor = useCallback(async () => {
    const result = await activateEmergencyCorridor({ intersections, roads, metrics });
    setIntersections(result.intersections);
    setMetrics(result.metrics);
    setEmergencyCorridorActive(true);
    setLatestNotification({
      type: 'EMERGENCY',
      title: '🚨 Emergency Green Corridor Active',
      message: 'Ambulance A-17 route secured (I1 → I2 → I5 → I4 → Hospital). ETA: 7m 18s.',
    });
  }, [intersections, roads, metrics]);

  // Restore Normal Traffic from Corridor
  const handleRestoreTraffic = useCallback(async () => {
    const result = await restoreTraffic(intersections);
    setIntersections(result.intersections);
    setEmergencyCorridorActive(false);
    setLatestNotification({
      type: 'INFO',
      title: 'Normal Signal Operations Restored',
      message: 'Emergency preemption cleared across all route segments.',
    });
  }, [intersections]);

  const dismissNotification = () => setLatestNotification(null);

  const selectedIntersection = intersections[selectedIntersectionId] || intersections.I1;

  const value = {
    intersections,
    setIntersections,
    roads,
    metrics,
    isOptimized,
    isOptimizing,
    optimizationResult,
    emergencyCorridorActive,
    emergencyRoute: EMERGENCY_ROUTE,
    selectedIntersectionId,
    setSelectedIntersectionId,
    selectedIntersection,
    activeEvents,
    latestNotification,
    dismissNotification,
    simulationTime: formatSimTime(simTimeSeconds),
    systemStatus: 'ONLINE',
    quantumEngineStatus: 'READY',
    handleRunOptimization,
    handleApplyOptimization,
    handleResetSignals,
    handleTriggerEvent,
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
