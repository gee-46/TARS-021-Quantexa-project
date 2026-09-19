// Service / API Abstraction for QuantumForce
// Designed for seamless integration with Python FastAPI / Streamlit / Qiskit / SUMO services

import { INITIAL_INTERSECTIONS, INITIAL_ROADS, EMERGENCY_ROUTE } from './networkGraph';

// Default / Baseline State
export const BASELINE_METRICS = {
  avgWaitTime: 54.2, // seconds
  queueLength: 145, // total vehicles queued
  throughput: 3420, // vehicles / hour
  fuelConsumption: 482.5, // liters / hour
  co2Emissions: 1128.0, // kg CO2 / hour
  emergencyEta: '11m 42s',
  emergencyEtaSeconds: 702,
};

export const OPTIMIZED_METRICS = {
  avgWaitTime: 33.6, // -38.0%
  queueLength: 82, // -43.4%
  throughput: 4680, // +36.8%
  fuelConsumption: 362.0, // -25.0%
  co2Emissions: 846.0, // -25.0%
  emergencyEta: '7m 18s',
  emergencyEtaSeconds: 438,
};

/**
 * Fetches current traffic state
 */
export async function getTrafficState() {
  // In production, this can call: await fetch('http://localhost:8000/api/traffic/state')
  return {
    intersections: { ...INITIAL_INTERSECTIONS },
    roads: [...INITIAL_ROADS],
    metrics: { ...BASELINE_METRICS },
    simulationTime: 'T+00:14:32',
    status: 'ONLINE',
    quantumEngine: 'READY',
  };
}

/**
 * Executes Hybrid QAOA / QUBO Signal Optimization
 */
export async function runQuantumOptimization(currentState) {
  // Simulates QAOA execution stages on Qiskit Aer
  return new Promise((resolve) => {
    setTimeout(() => {
      const optimizedIntersections = {};
      Object.entries(currentState.intersections).forEach(([id, data]) => {
        optimizedIntersections[id] = {
          ...data,
          density: Math.max(15, Math.round(data.density * 0.65)),
          queue: Math.max(2, Math.round(data.queue * 0.55)),
          capacity: Math.max(25, Math.round(data.capacity * 0.7)),
          signal: data.optimizedSignal || (data.signal === 'RED' ? 'GREEN' : data.signal),
          signalDuration: data.optimizedDuration || 55,
          avgWaitTime: Math.max(12, Math.round(data.avgWaitTime * 0.62)),
        };
      });

      resolve({
        success: true,
        method: 'Hybrid QAOA (Qiskit Aer Simulator)',
        formulation: 'QUBO / Ising Hamiltonian',
        variables: 24,
        constraints: 12,
        costFunctionValue: -1842.38,
        convergenceIterations: 14,
        executionTimeMs: 382,
        optimizedIntersections,
        optimizedMetrics: { ...OPTIMIZED_METRICS },
        pipelineStages: [
          { name: 'Traffic state collected', status: 'done', detail: '6 intersections, 8 arterial corridors' },
          { name: 'Network graph encoded', status: 'done', detail: 'Adjacency matrix & capacity constraints' },
          { name: 'QUBO formulated', status: 'done', detail: '24 binary variables, 12 quadratic penalty terms' },
          { name: 'Running QAOA simulation', status: 'done', detail: 'Depth p=3 on Qiskit Aer statevector' },
          { name: 'Optimal bitstring extracted', status: 'done', detail: 'Global minimum cost -1842.38' },
          { name: 'Signal schedule generated', status: 'done', detail: 'Synchronized green-wave timing active' },
        ],
      });
    }, 1800);
  });
}

/**
 * Applies optimized signals to active traffic network
 */
export async function applyOptimizedSignals(optimizedData) {
  return {
    intersections: optimizedData.optimizedIntersections,
    metrics: optimizedData.optimizedMetrics,
    isOptimized: true,
  };
}

/**
 * Triggers dynamic traffic events (Accident, Sudden Congestion, Road Closure, Emergency)
 */
export async function triggerTrafficEvent(eventType, currentState) {
  const updatedIntersections = { ...currentState.intersections };
  const updatedRoads = [...currentState.roads];
  let newMetrics = { ...currentState.metrics };
  let eventDetail = {};

  switch (eventType) {
    case 'CONGESTION':
      updatedIntersections.I3 = {
        ...updatedIntersections.I3,
        density: 96,
        queue: 64,
        capacity: 98,
        signal: 'RED',
        signalDuration: 70,
        avgWaitTime: 92,
      };
      updatedIntersections.I1 = {
        ...updatedIntersections.I1,
        density: 88,
        queue: 38,
        avgWaitTime: 68,
      };
      newMetrics.avgWaitTime = 68.4;
      newMetrics.queueLength = 186;
      newMetrics.throughput = 2850;
      eventDetail = {
        type: 'SUDDEN_CONGESTION',
        title: '⚠ Sudden Congestion Surge',
        location: 'I3 (Quantum Plaza) & I1 Corridor',
        description: 'Peak vehicle arrival surge detected on West Corridor. Queues increased by 42%.',
        timestamp: new Date().toLocaleTimeString(),
        severity: 'HIGH',
      };
      break;

    case 'ACCIDENT':
      updatedIntersections.I3 = {
        ...updatedIntersections.I3,
        density: 98,
        queue: 58,
        capacity: 100,
        signal: 'RED',
        avgWaitTime: 110,
      };
      updatedRoads[1] = { ...updatedRoads[1], congestion: 'blocked' };
      newMetrics.avgWaitTime = 74.5;
      newMetrics.queueLength = 205;
      newMetrics.throughput = 2410;
      eventDetail = {
        type: 'ACCIDENT',
        title: '🚨 Collision Reported at I3',
        location: 'Intersection I3 (Quantum Plaza West)',
        description: 'Multi-vehicle collision blocking two westbound lanes. Capacity bottleneck triggered.',
        timestamp: new Date().toLocaleTimeString(),
        severity: 'CRITICAL',
      };
      break;

    case 'ROAD_CLOSURE':
      updatedRoads[4] = { ...updatedRoads[4], congestion: 'closed' };
      updatedIntersections.I3 = { ...updatedIntersections.I3, density: 85, queue: 44 };
      updatedIntersections.I4 = { ...updatedIntersections.I4, density: 89, queue: 48 };
      newMetrics.avgWaitTime = 63.8;
      newMetrics.queueLength = 172;
      eventDetail = {
        type: 'ROAD_CLOSURE',
        title: '🚧 Road Closure Maintenance',
        location: 'South Valley Way (I3 - I4)',
        description: 'Emergency municipal maintenance closing R5 artery. Rerouting required.',
        timestamp: new Date().toLocaleTimeString(),
        severity: 'MEDIUM',
      };
      break;

    case 'EMERGENCY_VEHICLE':
      eventDetail = {
        type: 'EMERGENCY_VEHICLE',
        title: '🚑 Ambulance A-17 Dispatched',
        location: 'Origin: I1 → Destination: City Hospital',
        description: 'Critical patient transit en route to City Hospital. Green corridor requested.',
        timestamp: new Date().toLocaleTimeString(),
        severity: 'EMERGENCY',
      };
      break;

    default:
      break;
  }

  return {
    intersections: updatedIntersections,
    roads: updatedRoads,
    metrics: newMetrics,
    event: eventDetail,
  };
}

/**
 * Activates Emergency Green Corridor for Ambulance A-17
 */
export async function activateEmergencyCorridor(currentState) {
  const updatedIntersections = { ...currentState.intersections };

  EMERGENCY_ROUTE.forEach((id) => {
    if (updatedIntersections[id]) {
      updatedIntersections[id] = {
        ...updatedIntersections[id],
        signal: 'GREEN',
        signalDuration: 120,
        isCorridorActive: true,
      };
    }
  });

  const updatedMetrics = {
    ...currentState.metrics,
    emergencyEta: '7m 18s',
    emergencyEtaSeconds: 438,
  };

  return {
    intersections: updatedIntersections,
    metrics: updatedMetrics,
    corridorActive: true,
    affectedIntersections: ['I1', 'I2', 'I5', 'I4'],
    savedTime: '4m 24s',
  };
}

/**
 * Restores Normal Traffic Operation
 */
export async function restoreTraffic(originalIntersections) {
  const restored = {};
  Object.entries(originalIntersections).forEach(([id, data]) => {
    restored[id] = {
      ...data,
      isCorridorActive: false,
      signal: INITIAL_INTERSECTIONS[id]?.signal || 'GREEN',
    };
  });

  return {
    intersections: restored,
    metrics: { ...BASELINE_METRICS },
    corridorActive: false,
    isOptimized: false,
  };
}

/**
 * Analytics Dataset for Before/After & Time-series
 */
export function getAnalyticsData(isOptimized) {
  const factor = isOptimized ? 0.65 : 1.0;
  return {
    timeSeries: [
      { time: '08:00', classicalWait: 48, quantumWait: 32, throughputClassical: 3200, throughputQuantum: 4400 },
      { time: '08:15', classicalWait: 58, quantumWait: 36, throughputClassical: 3100, throughputQuantum: 4600 },
      { time: '08:30', classicalWait: 74, quantumWait: 38, throughputClassical: 2800, throughputQuantum: 4800 },
      { time: '08:45', classicalWait: 82, quantumWait: 41, throughputClassical: 2700, throughputQuantum: 4950 },
      { time: '09:00', classicalWait: 66, quantumWait: 34, throughputClassical: 3300, throughputQuantum: 4700 },
      { time: '09:15', classicalWait: 52, quantumWait: 30, throughputClassical: 3500, throughputQuantum: 4750 },
    ],
    emissionsData: [
      { category: 'CO2 (kg/hr)', classical: 1128, quantum: 846, improvement: '-25.0%' },
      { category: 'NOx (g/hr)', classical: 412, quantum: 295, improvement: '-28.4%' },
      { category: 'Fuel (L/hr)', classical: 482.5, quantum: 362, improvement: '-25.0%' },
      { category: 'Idle Time (%)', classical: 42.6, quantum: 21.2, improvement: '-50.2%' },
    ],
    kpiComparisons: [
      { metric: 'Average Waiting Time', classical: '54.2 s', quantum: '33.6 s', diff: '-38.0%', better: true },
      { metric: 'Total Queued Vehicles', classical: '145 veh', quantum: '82 veh', diff: '-43.4%', better: true },
      { metric: 'Traffic Throughput', classical: '3,420 veh/h', quantum: '4,680 veh/h', diff: '+36.8%', better: true },
      { metric: 'Fuel Consumption', classical: '482.5 L/h', quantum: '362.0 L/h', diff: '-25.0%', better: true },
      { metric: 'CO₂ Emissions', classical: '1,128 kg/h', quantum: '846 kg/h', diff: '-25.0%', better: true },
      { metric: 'Ambulance ETA', classical: '11m 42s', quantum: '7m 18s', diff: '-37.6%', better: true },
    ],
  };
}
