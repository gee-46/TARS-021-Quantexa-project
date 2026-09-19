export type IntersectionId = string;
export type RoadId = string;

export type VehicleType = 'normal' | 'ambulance' | 'fire_truck' | 'police';

export interface Vehicle {
  id: string;
  type: VehicleType;
  priority: number; // normal: 0, police: 60, fire_truck: 80, ambulance: 100
  route: IntersectionId[];
  currentHopIndex: number; // current position in route: route[currentHopIndex] -> route[currentHopIndex + 1]
  spawnTick: number;
  departureTick: number;
  totalWaitTime: number;
  queueJumpedCount: number;
  hasJumpedCurrentQueue: boolean;
  color: string;
  arrived: boolean;
  arrivedTick?: number;
}

export type RoadStatus = 'normal' | 'accident' | 'congestion' | 'closure';

export interface Road {
  id: RoadId;
  from: IntersectionId;
  to: IntersectionId;
  capacityPerTick: number;
  baseCapacity: number;
  status: RoadStatus;
  speedMultiplier: number; // 1.0 = normal, 0.5 = congestion, 0 = accident/closure
  vehicles: Vehicle[]; // FIFO queue (with preemption when queue jumping is enabled)
}

export interface Intersection {
  id: IntersectionId;
  label: string;
  x: number;
  y: number;
  incomingRoads: RoadId[];
  outgoingDirections: IntersectionId[];
  currentGreen: IntersectionId | null; // which outgoing direction has green light
  forcedGreen: IntersectionId | null; // override from emergency or optimizer
  phaseTick: number;
  roundRobinIndex: number;
}

export interface EmergencyEvent {
  eventId: string;
  vehicleId: string;
  type: VehicleType;
  route: IntersectionId[];
  priority: number;
  status: 'reported' | 'assigned' | 'priority_active' | 'corridor_active' | 'moving' | 'cleared';
  spawnTick: number;
  arrivedTick: number | null;
  corridorSatisfied: boolean;
}

export interface EmergencyConstraints {
  active: boolean;
  priority_intersections: IntersectionId[];
  corridor_hops: [IntersectionId, IntersectionId][];
  vehicles: {
    id: string;
    type: VehicleType;
    route: IntersectionId[];
    priority: number;
  }[];
}

export type ControllerType =
  | 'qaoa_xy'
  | 'qaoa_x'
  | 'exact_qubo'
  | 'simulated_annealing'
  | 'greedy_qubo'
  | 'rule_based'
  | 'direct_corridor'
  | 'fixed_timing';

export interface SignalPlan {
  [intersectionId: IntersectionId]: IntersectionId; // intersectionId -> chosen outgoing direction
}

export interface SolverResult {
  solver: string;
  plan: SignalPlan;
  energy: number;
  feasible: boolean;
  solveTimeMs: number;
  info: {
    prob_feasible?: number;
    prob_optimal?: number;
    uniform_prob_optimal?: number;
    approx_ratio?: number;
    n_evals?: number;
    p?: number;
    mixer?: string;
    bitstring?: string;
  };
}

export interface BenchmarkRow {
  controller: string;
  label: string;
  type: ControllerType;
  mean_trip_ticks: number;
  mean_queue_length: number;
  vehicles_remaining: number;
  completed_trips: number;
  ambulance_transit_ticks: number | null;
  ambulance_queue_jumps: number;
  fuel_wasted_liters: number;
  co2_emissions_kg: number;
  energy_savings_percent: number;
}

export interface LogEntry {
  id: string;
  tick: number;
  type: 'emergency' | 'signal' | 'hazard' | 'queue_jump' | 'system';
  message: string;
  severity?: 'info' | 'warning' | 'emergency' | 'success';
}
