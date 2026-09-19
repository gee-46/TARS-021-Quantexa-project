import {
  Intersection,
  IntersectionId,
  Road,
  RoadId,
  Vehicle,
  VehicleType,
  EmergencyEvent,
  EmergencyConstraints,
  LogEntry,
} from '../types/traffic';

export class TrafficNetwork {
  intersections: Map<IntersectionId, Intersection> = new Map();
  roads: Map<RoadId, Road> = new Map();

  constructor() {
    this.buildDefaultGrid();
  }

  buildDefaultGrid(rows = 2, cols = 3, capacityPerTick = 2) {
    this.intersections.clear();
    this.roads.clear();

    // 2x3 Grid:
    // I1 -- I2 -- I3
    // |    |    |
    // I4 -- I5 -- I6
    const coords: Record<string, { x: number; y: number }> = {
      I1: { x: 120, y: 100 },
      I2: { x: 380, y: 100 },
      I3: { x: 640, y: 100 },
      I4: { x: 120, y: 320 },
      I5: { x: 380, y: 320 },
      I6: { x: 640, y: 320 },
    };

    let idx = 1;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const id = `I${idx++}`;
        const pos = coords[id] || { x: 100 + c * 260, y: 100 + r * 220 };
        this.intersections.set(id, {
          id,
          label: id,
          x: pos.x,
          y: pos.y,
          incomingRoads: [],
          outgoingDirections: [],
          currentGreen: null,
          forcedGreen: null,
          phaseTick: 0,
          roundRobinIndex: 0,
        });
      }
    }

    // Grid connectivity
    const edges: [IntersectionId, IntersectionId][] = [
      ['I1', 'I2'],
      ['I2', 'I3'],
      ['I4', 'I5'],
      ['I5', 'I6'],
      ['I1', 'I4'],
      ['I2', 'I5'],
      ['I3', 'I6'],
    ];

    for (const [a, b] of edges) {
      this.addBidirectionalRoad(a, b, capacityPerTick);
    }

    // Set initial signal greens
    for (const inter of this.intersections.values()) {
      if (inter.outgoingDirections.length > 0) {
        inter.currentGreen = inter.outgoingDirections[0];
      }
    }
  }

  addBidirectionalRoad(from: IntersectionId, to: IntersectionId, capacity: number) {
    this.addRoad(from, to, capacity);
    this.addRoad(to, from, capacity);
  }

  addRoad(from: IntersectionId, to: IntersectionId, capacity: number) {
    const id = `${from}->${to}`;
    const road: Road = {
      id,
      from,
      to,
      capacityPerTick: capacity,
      baseCapacity: capacity,
      status: 'normal',
      speedMultiplier: 1.0,
      vehicles: [],
    };
    this.roads.set(id, road);

    const fromInter = this.intersections.get(from);
    if (fromInter && !fromInter.outgoingDirections.includes(to)) {
      fromInter.outgoingDirections.push(to);
    }

    const toInter = this.intersections.get(to);
    if (toInter && !toInter.incomingRoads.includes(id)) {
      toInter.incomingRoads.push(id);
    }
  }

  getRoad(from: IntersectionId, to: IntersectionId): Road | undefined {
    return this.roads.get(`${from}->${to}`);
  }

  shortestRoute(start: IntersectionId, end: IntersectionId): IntersectionId[] {
    if (start === end) return [start];
    const queue: IntersectionId[][] = [[start]];
    const visited = new Set<IntersectionId>([start]);

    while (queue.length > 0) {
      const path = queue.shift()!;
      const curr = path[path.length - 1];
      const inter = this.intersections.get(curr);
      if (!inter) continue;

      for (const next of inter.outgoingDirections) {
        if (next === end) {
          return [...path, next];
        }
        if (!visited.has(next)) {
          visited.add(next);
          queue.push([...path, next]);
        }
      }
    }
    return [start, end];
  }
}

export class EmergencyManager {
  events: Map<string, EmergencyEvent> = new Map();
  private nextId = 1;

  reportVehicle(
    type: VehicleType,
    route: IntersectionId[],
    currentTick: number,
    customId?: string
  ): EmergencyEvent {
    const eventId = `EV_${this.nextId++}`;
    const vehicleId = customId || (type === 'ambulance' ? `AMB_${String(this.nextId).padStart(2, '0')}` : `${type.toUpperCase().slice(0, 3)}_${String(this.nextId).padStart(2, '0')}`);
    const priority = type === 'ambulance' ? 100 : type === 'fire_truck' ? 80 : type === 'police' ? 60 : 0;

    const event: EmergencyEvent = {
      eventId,
      vehicleId,
      type,
      route,
      priority,
      status: 'corridor_active',
      spawnTick: currentTick,
      arrivedTick: null,
      corridorSatisfied: true,
    };
    this.events.set(eventId, event);
    return event;
  }

  clear(eventId: string) {
    const ev = this.events.get(eventId);
    if (ev) {
      ev.status = 'cleared';
    }
  }

  getConstraints(): EmergencyConstraints {
    const activeEvents = Array.from(this.events.values()).filter(
      (e) => e.status !== 'cleared' && e.arrivedTick === null
    );

    if (activeEvents.length === 0) {
      return {
        active: false,
        priority_intersections: [],
        corridor_hops: [],
        vehicles: [],
      };
    }

    const priorityIntersections = new Set<IntersectionId>();
    const corridorHops: [IntersectionId, IntersectionId][] = [];
    const vehicles: EmergencyConstraints['vehicles'] = [];

    for (const ev of activeEvents) {
      vehicles.push({
        id: ev.vehicleId,
        type: ev.type,
        route: ev.route,
        priority: ev.priority,
      });

      for (let i = 0; i < ev.route.length; i++) {
        priorityIntersections.add(ev.route[i]);
        if (i < ev.route.length - 1) {
          corridorHops.push([ev.route[i], ev.route[i + 1]]);
        }
      }
    }

    return {
      active: true,
      priority_intersections: Array.from(priorityIntersections),
      corridor_hops: corridorHops,
      vehicles,
    };
  }
}

export class TrafficSimulator {
  network: TrafficNetwork;
  emergencyManager: EmergencyManager;
  vehicles: Map<string, Vehicle> = new Map();
  completedTrips = 0;
  totalWaitTime = 0;
  tickCount = 0;
  logs: LogEntry[] = [];
  
  // THE CRITICAL TOGGLE: Queue Jumping Preemption
  queueJumpingEnabled = true;

  // Environmental impact stats
  totalFuelWastedLiters = 0; // ~0.0006 liters idle fuel per tick per waiting car
  totalCO2EmissionsKg = 0; // ~1.4g CO2 per tick per waiting car
  totalQueueJumps = 0;

  // Pre-calculated ambulance stats for comparison
  lastAmbulanceTransitTicks: number | null = null;
  ambulanceTripHistory: { id: string; transitTicks: number; queueJumps: number; queueJumping: boolean }[] = [];

  constructor(network?: TrafficNetwork, emergencyManager?: EmergencyManager) {
    this.network = network || new TrafficNetwork();
    this.emergencyManager = emergencyManager || new EmergencyManager();
  }

  log(message: string, type: LogEntry['type'] = 'system', severity: LogEntry['severity'] = 'info') {
    const entry: LogEntry = {
      id: `log_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      tick: this.tickCount,
      type,
      message,
      severity,
    };
    this.logs.unshift(entry);
    if (this.logs.length > 100) {
      this.logs.pop();
    }
  }

  spawnVehicle(route: IntersectionId[], type: VehicleType = 'normal', vehicleId?: string): Vehicle | null {
    if (route.length < 2) return null;
    const from = route[0];
    const to = route[1];
    const road = this.network.getRoad(from, to);
    if (!road) return null;

    const id = vehicleId || `V_${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
    const priority = type === 'ambulance' ? 100 : type === 'fire_truck' ? 80 : type === 'police' ? 60 : 0;
    
    // Assign colors
    const color =
      type === 'ambulance'
        ? '#ef4444' // Crimson red / siren
        : type === 'fire_truck'
        ? '#f97316' // Orange fire
        : type === 'police'
        ? '#3b82f6' // Blue police
        : '#94a3b8'; // Slate normal

    const vehicle: Vehicle = {
      id,
      type,
      priority,
      route,
      currentHopIndex: 0,
      spawnTick: this.tickCount,
      departureTick: this.tickCount,
      totalWaitTime: 0,
      queueJumpedCount: 0,
      hasJumpedCurrentQueue: false,
      color,
      arrived: false,
    };

    this.vehicles.set(id, vehicle);

    // Enqueue onto road with Queue Jumping check
    this.enqueueVehicle(road, vehicle);

    if (type !== 'normal') {
      this.log(`🚨 Emergency vehicle [${id}] dispatched along route ${route.join(' → ')}`, 'emergency', 'emergency');
    }

    return vehicle;
  }

  // KEY FEATURE: Enqueue vehicle onto road with Preemption / Queue Jumping
  private enqueueVehicle(road: Road, vehicle: Vehicle) {
    if (vehicle.type !== 'normal' && this.queueJumpingEnabled) {
      // Find position ahead of lower-priority vehicles
      let insertIndex = 0;
      while (insertIndex < road.vehicles.length && road.vehicles[insertIndex].priority >= vehicle.priority) {
        insertIndex++;
      }
      
      const overtaken = road.vehicles.length - insertIndex;
      road.vehicles.splice(insertIndex, 0, vehicle);
      
      if (overtaken > 0) {
        vehicle.queueJumpedCount += overtaken;
        vehicle.hasJumpedCurrentQueue = true;
        this.totalQueueJumps += overtaken;
        this.log(
          `⚡ [QUEUE PREEMPTION] ${vehicle.type.toUpperCase()} ${vehicle.id} jumped ${overtaken} vehicle(s) on ${road.id} to position #${insertIndex + 1}!`,
          'queue_jump',
          'success'
        );
      }
    } else {
      // Standard FIFO without preemption
      road.vehicles.push(vehicle);
    }
  }

  // Preempt / jump queue on all roads where emergency vehicles are stuck behind normal traffic
  applyQueueJumpingSweep() {
    if (!this.queueJumpingEnabled) return;

    for (const road of this.network.roads.values()) {
      if (road.vehicles.length <= 1) continue;

      // Check if any emergency vehicle is behind a normal vehicle
      let needSort = false;
      for (let i = 0; i < road.vehicles.length - 1; i++) {
        if (road.vehicles[i].priority < road.vehicles[i + 1].priority) {
          needSort = true;
          break;
        }
      }

      if (needSort) {
        // Stable partition: preserve relative order within same priority
        const originalPositions = new Map(road.vehicles.map((v, idx) => [v.id, idx]));
        road.vehicles.sort((a, b) => b.priority - a.priority);

        for (const v of road.vehicles) {
          if (v.type !== 'normal') {
            const oldPos = originalPositions.get(v.id) ?? 0;
            const newPos = road.vehicles.indexOf(v);
            if (newPos < oldPos) {
              const jumped = oldPos - newPos;
              v.queueJumpedCount += jumped;
              v.hasJumpedCurrentQueue = true;
              this.totalQueueJumps += jumped;
              this.log(
                `⚡ [QUEUE PREEMPTION] ${v.type.toUpperCase()} ${v.id} bypassed ${jumped} cars on ${road.id}!`,
                'queue_jump',
                'success'
              );
            }
          }
        }
      }
    }
  }

  // One discrete simulation tick
  tick() {
    this.tickCount++;

    // 1. Run Queue-jumping sweep if preemption is active
    if (this.queueJumpingEnabled) {
      this.applyQueueJumpingSweep();
    }

    // 2. Snapshot queue departures (ensuring at most ONE hop per vehicle per tick)
    // To prevent a vehicle from skipping through multiple intersections in one tick,
    // we determine which vehicles depart based strictly on the snapshot at tick start.
    const departures: { vehicle: Vehicle; fromRoad: Road; nextHop: IntersectionId | null }[] = [];

    for (const inter of this.network.intersections.values()) {
      const activeGreen = inter.forcedGreen ?? inter.currentGreen;
      if (!activeGreen) continue;

      // Find incoming road that leads towards activeGreen or whose vehicles want to move towards activeGreen
      for (const roadId of inter.incomingRoads) {
        const road = this.network.roads.get(roadId);
        if (!road || road.capacityPerTick <= 0 || road.vehicles.length === 0) continue;

        // Number of vehicles this road can emit this tick
        let allowed = road.capacityPerTick;
        let examined = 0;
        const remainingVehicles: Vehicle[] = [];

        for (const v of road.vehicles) {
          const nextTarget = v.route[v.currentHopIndex + 1];
          // Check if vehicle wants to go to activeGreen
          if (nextTarget === activeGreen && examined < allowed) {
            departures.push({
              vehicle: v,
              fromRoad: road,
              nextHop: v.route[v.currentHopIndex + 2] ?? null,
            });
            examined++;
          } else {
            remainingVehicles.push(v);
          }
        }
        road.vehicles = remainingVehicles;
      }
    }

    // 3. Process the departures: advance them to the next road or complete trip
    for (const dep of departures) {
      const v = dep.vehicle;
      v.currentHopIndex++;
      v.hasJumpedCurrentQueue = false;

      // Did the vehicle reach destination?
      if (v.currentHopIndex >= v.route.length - 1) {
        v.arrived = true;
        v.arrivedTick = this.tickCount;
        this.completedTrips++;
        this.vehicles.delete(v.id);

        if (v.type === 'ambulance') {
          const transitTicks = this.tickCount - v.spawnTick;
          this.lastAmbulanceTransitTicks = transitTicks;
          this.ambulanceTripHistory.push({
            id: v.id,
            transitTicks,
            queueJumps: v.queueJumpedCount,
            queueJumping: this.queueJumpingEnabled,
          });
          this.log(
            `🏁 [AMBULANCE ARRIVED] ${v.id} reached destination in ${transitTicks} ticks! (Bypassed ${v.queueJumpedCount} cars)`,
            'emergency',
            'success'
          );
        } else if (v.type !== 'normal') {
          this.log(`🏁 ${v.type.toUpperCase()} ${v.id} arrived at destination in ${this.tickCount - v.spawnTick} ticks.`, 'emergency', 'success');
        }
      } else {
        // Enqueue onto next road
        const nextFrom = v.route[v.currentHopIndex];
        const nextTo = v.route[v.currentHopIndex + 1];
        const nextRoad = this.network.getRoad(nextFrom, nextTo);
        if (nextRoad) {
          this.enqueueVehicle(nextRoad, v);
        }
      }
    }

    // 4. Update wait time & fuel/CO2 emissions for all vehicles still waiting in queues
    let waitingThisTick = 0;
    for (const road of this.network.roads.values()) {
      for (const v of road.vehicles) {
        v.totalWaitTime++;
        this.totalWaitTime++;
        waitingThisTick++;
      }
    }

    // Environmental metrics accumulation:
    // Fuel wasted in idling: ~0.0006 L/tick per queued car
    // CO2 emissions: ~1.4 g (0.0014 kg) per tick per queued car
    this.totalFuelWastedLiters += waitingThisTick * 0.0006;
    this.totalCO2EmissionsKg += waitingThisTick * 0.0014;

    // Check emergency manager events
    const constraints = this.emergencyManager.getConstraints();
    for (const ev of this.emergencyManager.events.values()) {
      if (ev.status !== 'cleared' && ev.arrivedTick === null) {
        const v = this.vehicles.get(ev.vehicleId);
        if (!v || v.arrived) {
          ev.arrivedTick = this.tickCount;
          ev.status = 'cleared';
        }
      }
    }

    // Normal signal rotation if not controlled by QUBO or forced
    for (const inter of this.network.intersections.values()) {
      if (inter.forcedGreen === null) {
        inter.phaseTick++;
        if (inter.phaseTick >= 4) { // 4 ticks per green phase in normal mode
          inter.phaseTick = 0;
          if (inter.outgoingDirections.length > 0) {
            inter.roundRobinIndex = (inter.roundRobinIndex + 1) % inter.outgoingDirections.length;
            inter.currentGreen = inter.outgoingDirections[inter.roundRobinIndex];
          }
        }
      }
    }
  }

  // Applies a full signal plan from optimizer/controller
  applySignalPlan(plan: Record<IntersectionId, IntersectionId>) {
    for (const [interId, greenDir] of Object.entries(plan)) {
      const inter = this.network.intersections.get(interId);
      if (inter) {
        inter.forcedGreen = greenDir;
        inter.currentGreen = greenDir;
      }
    }
  }

  clearForcedGreens() {
    for (const inter of this.network.intersections.values()) {
      inter.forcedGreen = null;
    }
  }

  applyAccident(from: IntersectionId, to: IntersectionId) {
    const road = this.network.getRoad(from, to);
    if (road) {
      road.capacityPerTick = 0;
      road.speedMultiplier = 0;
      road.status = 'accident';
      this.log(`⚠️ Accident reported on ${from} → ${to}! Capacity reduced to 0.`, 'hazard', 'warning');
    }
  }

  applyCongestion(from: IntersectionId, to: IntersectionId, factor = 0.5) {
    const road = this.network.getRoad(from, to);
    if (road) {
      road.capacityPerTick = Math.max(1, Math.floor(road.baseCapacity * factor));
      road.speedMultiplier = factor;
      road.status = 'congestion';
      this.log(`⚠️ Congestion reported on ${from} → ${to}. Capacity reduced by ${(1 - factor) * 100}%.`, 'hazard', 'warning');
    }
  }

  applyClosure(from: IntersectionId, to: IntersectionId) {
    const road = this.network.getRoad(from, to);
    if (road) {
      road.capacityPerTick = 0;
      road.speedMultiplier = 0;
      road.status = 'closure';
      this.log(`⛔ Road closed on ${from} → ${to}.`, 'hazard', 'warning');
    }
  }

  clearHazard(from: IntersectionId, to: IntersectionId) {
    const road = this.network.getRoad(from, to);
    if (road) {
      road.capacityPerTick = road.baseCapacity;
      road.speedMultiplier = 1.0;
      road.status = 'normal';
      this.log(`✅ Hazard cleared on ${from} → ${to}. Capacity restored to ${road.baseCapacity}.`, 'hazard', 'info');
    }
  }

  getNetworkState() {
    const intersectionsObj: Record<string, any> = {};
    for (const [id, inter] of this.network.intersections.entries()) {
      intersectionsObj[id] = {
        signal_state: inter.currentGreen,
        forced_green: inter.forcedGreen,
        outgoing_directions: inter.outgoingDirections,
      };
    }

    const roadsObj: Record<string, any> = {};
    for (const [id, road] of this.network.roads.entries()) {
      roadsObj[id] = {
        queue_length: road.vehicles.length,
        density: road.vehicles.length / (road.baseCapacity * 5),
        capacity_per_tick: road.capacityPerTick,
        status: road.status,
      };
    }

    return {
      intersections: intersectionsObj,
      roads: roadsObj,
      tick: this.tickCount,
      active_vehicles: this.vehicles.size,
      completed_trips: this.completedTrips,
      total_wait_time: this.totalWaitTime,
      queue_jumping_enabled: this.queueJumpingEnabled,
    };
  }

  // Spawns background random traffic
  spawnRandomBackgroundDemand(count = 3) {
    const nodes = Array.from(this.network.intersections.keys());
    for (let i = 0; i < count; i++) {
      const a = nodes[Math.floor(Math.random() * nodes.length)];
      let b = nodes[Math.floor(Math.random() * nodes.length)];
      while (b === a) {
        b = nodes[Math.floor(Math.random() * nodes.length)];
      }
      const route = this.network.shortestRoute(a, b);
      this.spawnVehicle(route, 'normal');
    }
  }
}
