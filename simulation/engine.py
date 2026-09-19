"""Discrete-Time Microscopic Traffic Simulation Engine for 4-Intersection Grid.

Executes second-by-second traffic progression through network queues and signal phases:
- Queues at I1, I2, I3, I4.
- People-aware passenger tracking (cars, buses, trucks, motorcycles, emergency).
- Cyclic green/red signal operation based on allocated durations (15s, 30s, 45s).
- Deterministic Poisson / scheduled arrivals from seed.
- Intersection-to-intersection transit pipelines.
- Multi-emergency corridor preemption with conflict arbitration.
- Continuous approach-level wait tracking, starvation detection, and Jain fairness calculation.
- Environmental emissions modeling (idling time, fuel burn, CO2 output).
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import numpy as np

from simulation.models import Vehicle, SignalState, VehicleTypeConfig
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from simulation.metrics import SimulationMetrics
from simulation.emergency_controller import EmergencyCorridorController
from simulation.emergency_events import EmergencyEventType
from optimization.traffic_objectives import calculate_jain_fairness_index
from simulation.emissions import calculate_emissions


class TrafficSimulator:
    """Deterministic, discrete-time microscopic traffic simulator for 4-intersection networks."""

    def __init__(
        self,
        scenario: SimulationScenario,
        enable_emergency_corridor: bool = False,
        prepare_lookahead_seconds: int = 3,
        adaptive_controller: Optional[Any] = None,
        vehicle_type_config: Optional[VehicleTypeConfig] = None,
        conflict_solver: str = "sa",
        preemption_duty: float = 1.0,
    ):
        self.conflict_solver = conflict_solver
        self.preemption_duty = preemption_duty
        self.scenario = scenario
        self.enable_emergency_corridor = enable_emergency_corridor
        self.prepare_lookahead_seconds = prepare_lookahead_seconds
        self.adaptive_controller = adaptive_controller
        self.vehicle_type_config = vehicle_type_config if vehicle_type_config is not None else scenario.vehicle_type_config
        self.last_emergency_controller: Optional[EmergencyCorridorController] = None
        self.last_adaptive_controller: Optional[Any] = None

    def simulate(
        self,
        signal_plan: Optional[Dict[str, int]] = None,
        seed: Optional[int] = None,
        adaptive_controller: Optional[Any] = None,
    ) -> SimulationMetrics:
        """Run discrete-time simulation of traffic flow under the specified signal plan or adaptive controller.

        Args:
            signal_plan: Map of intersection ID to green duration {"I1": 30, ...} (optional if adaptive_controller provided).
            seed: Deterministic random seed for arrival realization.
            adaptive_controller: Optional AdaptiveRollingHorizonController for continuous replanning.

        Returns:
            SimulationMetrics: Measured traffic performance outcomes.
        """
        active_adaptive = adaptive_controller if adaptive_controller is not None else self.adaptive_controller
        self.last_adaptive_controller = active_adaptive

        if active_adaptive is not None:
            if active_adaptive.current_plan is None:
                plan_to_use = active_adaptive.generate_initial_plan()
            else:
                plan_to_use = active_adaptive.current_plan
        else:
            if signal_plan is None:
                raise ValueError("signal_plan must be provided when adaptive_controller is None.")
            plan_to_use = signal_plan

        self.scenario.validate_plan(plan_to_use)
        signal_state = SignalState(plan=plan_to_use, cycle_length=self.scenario.cycle_length)
        rng = np.random.RandomState(seed if seed is not None else 42)

        # Initialize emergency corridor controller
        emergency_controller = EmergencyCorridorController(
            network_intersections=self.scenario.intersections,
            prepare_lookahead_seconds=self.prepare_lookahead_seconds,
            enabled=self.enable_emergency_corridor,
            conflict_solver=self.conflict_solver,
            preemption_duty=self.preemption_duty,
            travel_time_between_intersections=self.scenario.travel_time_between_intersections,
        )
        self.last_emergency_controller = emergency_controller

        intersections = self.scenario.intersections
        num_inter = len(intersections)
        inter_to_idx = {name: idx for idx, name in enumerate(intersections)}

        # Queues per intersection (FIFO order)
        queues: Dict[str, List[Vehicle]] = {name: [] for name in intersections}

        # Vehicles in transit between intersections: List of (vehicle, arrival_second, next_intersection)
        transit_pipes: List[Tuple[Vehicle, int, str]] = []

        all_vehicles: List[Vehicle] = []
        completed_vehicles: List[Vehicle] = []
        queue_history: List[Dict[str, int]] = []
        all_emergency_vehs: List[Vehicle] = []
        active_emergency_vehs: List[Vehicle] = []

        veh_type_cfg = self.vehicle_type_config
        veh_counter = 0

        # Helper to generate a regular vehicle
        def create_regular_vehicle(v_id: str, orig: str, dest: str, arr_t: int, rt: Tuple[str, ...]) -> Vehicle:
            bus_prob = self.scenario.bus_probabilities.get(orig, 0.0)
            if bus_prob > 0.0 and rng.rand() < bus_prob:
                v_type = "bus"
                passengers = int(round(veh_type_cfg.get_occupancy("bus")))
            else:
                v_type = "car"
                passengers = int(round(veh_type_cfg.get_occupancy("car")))

            return Vehicle(
                vehicle_id=v_id,
                origin=orig,
                destination=dest,
                arrival_time=arr_t,
                route=rt,
                current_step=0,
                is_emergency=False,
                vehicle_type=v_type,
                passenger_count=max(1, passengers),
            )

        # 1. Initialize initial queues at t=0
        for inter_name, count in self.scenario.initial_queues.items():
            if inter_name not in inter_to_idx:
                continue
            start_idx = inter_to_idx[inter_name]
            route = intersections[start_idx:]
            for _ in range(count):
                veh_counter += 1
                v = create_regular_vehicle(
                    v_id=f"INIT_{veh_counter:04d}",
                    orig=inter_name,
                    dest=intersections[-1],
                    arr_t=0,
                    rt=route,
                )
                queues[inter_name].append(v)
                all_vehicles.append(v)

        # Pre-index scheduled emergency vehicles
        all_emerg_configs = self.scenario.get_all_emergency_configs()
        emerg_arrival_map: Dict[int, List[EmergencyVehicleConfig]] = {}
        for e_cfg in all_emerg_configs:
            arr = e_cfg.arrival_time
            if arr not in emerg_arrival_map:
                emerg_arrival_map[arr] = []
            emerg_arrival_map[arr].append(e_cfg)

        # Approach-level wait tracker across entire simulation
        approach_wait_tracker: Dict[str, List[float]] = {name: [] for name in intersections}

        # Optional cross-street queues (served only while the arterial is red)
        cross_queues: Dict[str, List[Vehicle]] = {name: [] for name in intersections}
        cross_all: List[Vehicle] = []
        cross_counter = 0

        # 2. Discrete Time Step Simulation Loop
        for t in range(self.scenario.duration_seconds):
            # 0. Check scheduled adaptive rolling-horizon replanning at cycle boundary (t > 0)
            if active_adaptive is not None and (t % active_adaptive.replan_interval == 0) and t > 0:
                current_queues = {name: len(queues[name]) for name in intersections}
                person_queues = {name: sum(v.passenger_count for v in queues[name]) for name in intersections}

                # Approach wait estimate
                appr_waits = {}
                for name in intersections:
                    appr_waits[name] = max([v.waiting_time for v in queues[name]], default=0.0)

                new_plan = active_adaptive.step(
                    t=t,
                    current_queues=current_queues,
                    emergency_controller=emergency_controller,
                    person_queues=person_queues,
                    approach_waiting_times=appr_waits,
                )
                self.scenario.validate_plan(new_plan)
                signal_state = SignalState(plan=new_plan, cycle_length=self.scenario.cycle_length)

            # A. Spawn scheduled emergency vehicles at second t
            if t in emerg_arrival_map:
                for e_cfg in emerg_arrival_map[t]:
                    if e_cfg.route[0] not in inter_to_idx or e_cfg.route[-1] not in inter_to_idx:
                        continue
                    emergency_controller.validate_route(e_cfg.route)
                    e_veh = Vehicle(
                        vehicle_id=e_cfg.vehicle_id,
                        origin=e_cfg.route[0],
                        destination=e_cfg.route[-1],
                        arrival_time=t,
                        route=e_cfg.route,
                        current_step=0,
                        is_emergency=True,
                        vehicle_type="emergency",
                        passenger_count=int(round(veh_type_cfg.get_occupancy("emergency"))),
                        priority_level=e_cfg.priority,
                    )
                    queues[e_cfg.route[0]].append(e_veh)
                    all_vehicles.append(e_veh)
                    all_emergency_vehs.append(e_veh)
                    active_emergency_vehs.append(e_veh)

            # B. Spawn Poisson new vehicle arrivals at entrance intersections
            for entrance, rate in self.scenario.arrival_rates.items():
                if entrance in inter_to_idx and rate > 0:
                    start_idx = inter_to_idx[entrance]
                    route = intersections[start_idx:]
                    n_arrivals = rng.poisson(lam=rate)
                    for _ in range(n_arrivals):
                        veh_counter += 1
                        v = create_regular_vehicle(
                            v_id=f"VEH_{veh_counter:05d}",
                            orig=entrance,
                            dest=intersections[-1],
                            arr_t=t,
                            rt=route,
                        )
                        queues[entrance].append(v)
                        all_vehicles.append(v)

            # C. Update dynamic emergency corridor controller
            active_emergency_vehs = [v for v in active_emergency_vehs if not v.completed]
            emergency_controller.update(
                second=t,
                active_emergency_vehicle=active_emergency_vehs,
                transit_pipes=transit_pipes,
            )

            # D. Process vehicles arriving from transit pipes into downstream queues
            new_transit_pipes: List[Tuple[Vehicle, int, str]] = []
            for veh, arr_time, next_inter in transit_pipes:
                if t >= arr_time:
                    veh.current_step += 1
                    queues[next_inter].append(veh)
                else:
                    new_transit_pipes.append((veh, arr_time, next_inter))
            transit_pipes = new_transit_pipes

            # E. Service vehicles at intersections where signal is green
            for inter_name in intersections:
                is_normal_green = signal_state.is_green(inter_name, t)
                is_forced_green = emergency_controller.is_signal_green_forced(inter_name)
                is_green = is_normal_green or is_forced_green

                if is_green and len(queues[inter_name]) > 0:
                    capacity = int(self.scenario.service_rate)
                    served_count = min(capacity, len(queues[inter_name]))
                    for _ in range(served_count):
                        veh = queues[inter_name].pop(0)
                        if veh.is_at_destination:
                            veh.completed = True
                            veh.completion_time = t
                            completed_vehicles.append(veh)
                            if veh.is_emergency:
                                emergency_controller.update(
                                    second=t,
                                    active_emergency_vehicle=active_emergency_vehs,
                                    transit_pipes=transit_pipes,
                                )

                        else:
                            next_inter = veh.route[veh.current_step + 1]
                            arr_t = t + self.scenario.travel_time_between_intersections
                            transit_pipes.append((veh, arr_t, next_inter))

            # E2. Cross-street traffic: arrivals, then service only while the arterial is not green
            if self.scenario.cross_street_rates:
                for inter_name in intersections:
                    rate = self.scenario.cross_street_rates.get(inter_name, 0.0)
                    if rate > 0:
                        for _ in range(rng.poisson(lam=rate)):
                            cross_counter += 1
                            cv = Vehicle(
                                vehicle_id=f"CROSS_{cross_counter:05d}",
                                origin=inter_name,
                                destination=inter_name,
                                arrival_time=t,
                                route=(inter_name,),
                                passenger_count=max(1, int(round(veh_type_cfg.get_occupancy("car")))),
                            )
                            cross_queues[inter_name].append(cv)
                            cross_all.append(cv)
                    arterial_green = signal_state.is_green(inter_name, t) or emergency_controller.is_signal_green_forced(inter_name)
                    if not arterial_green:
                        for _ in range(min(int(self.scenario.service_rate), len(cross_queues[inter_name]))):
                            cross_queues[inter_name].pop(0)
                    for cv in cross_queues[inter_name]:
                        cv.waiting_time += 1

            # F. Update vehicle waiting and travel time metrics
            for inter_name, q_list in queues.items():
                for v in q_list:
                    v.waiting_time += 1
                if q_list:
                    max_w = max(v.waiting_time for v in q_list)
                    approach_wait_tracker[inter_name].append(max_w)

            for v in all_vehicles:
                if not v.completed:
                    v.travel_time += 1

            # G. Snapshot queue lengths
            snapshot = {name: len(queues[name]) for name in intersections}
            queue_history.append(snapshot)

        # 3. Calculate Comprehensive Simulation Metrics
        total_waiting_time = float(sum(v.waiting_time for v in all_vehicles))
        normal_waiting_time = float(sum(v.waiting_time for v in all_vehicles if not v.is_emergency))
        vehicles_generated = len(all_vehicles)
        vehicles_completed = len(completed_vehicles)
        avg_waiting_time = total_waiting_time / float(max(1, vehicles_generated))

        # Person Delay Metrics
        total_person_delay = float(sum(v.waiting_time * v.passenger_count for v in all_vehicles if not v.is_emergency))
        total_passengers = sum(v.passenger_count for v in all_vehicles if not v.is_emergency)
        avg_person_delay = total_person_delay / float(max(1, total_passengers))
        total_passengers_served = int(sum(v.passenger_count for v in completed_vehicles if not v.is_emergency))

        all_queue_counts = [count for snap in queue_history for count in snap.values()]
        max_q = max(all_queue_counts) if all_queue_counts else 0
        avg_q = float(np.mean([sum(snap.values()) for snap in queue_history])) if queue_history else 0.0

        # Approach Wait and Fairness
        mean_appr_waits = [
            float(np.mean(approach_wait_tracker[name])) if approach_wait_tracker[name] else 0.0
            for name in intersections
        ]
        jain_idx = calculate_jain_fairness_index(mean_appr_waits)
        max_appr_w = max([max(approach_wait_tracker[name]) if approach_wait_tracker[name] else 0.0 for name in intersections])
        starv_violations = sum(1 for waits in approach_wait_tracker.values() for w in waits if w > 120.0)

        # Environmental Emissions
        emissions = calculate_emissions(normal_waiting_time)

        primary_emerg = all_emergency_vehs[0] if all_emergency_vehs else None
        emergency_vehicle_results = [
            {
                "vehicle_id": ev.vehicle_id,
                "priority": ev.priority_level,
                "route": list(ev.route),
                "arrival_time": ev.arrival_time,
                "completed": ev.completed,
                "response_time": float(ev.completion_time - ev.arrival_time) if ev.completed and ev.completion_time is not None else None,
                "waiting_time": float(ev.waiting_time),
            }
            for ev in all_emergency_vehs
        ]
        cross_person_delay = float(sum(v.waiting_time * v.passenger_count for v in cross_all))

        emerg_wait: Optional[float] = None
        emerg_travel: Optional[float] = None
        emerg_resp: Optional[float] = None
        emerg_completed_flag = False

        if primary_emerg is not None:
            emerg_wait = float(primary_emerg.waiting_time)
            emerg_travel = float(primary_emerg.travel_time)
            emerg_completed_flag = primary_emerg.completed
            if primary_emerg.completed and primary_emerg.completion_time is not None:
                emerg_resp = float(primary_emerg.completion_time - primary_emerg.arrival_time)

        return SimulationMetrics(
            total_waiting_time=total_waiting_time,
            average_waiting_time=avg_waiting_time,
            max_queue=max_q,
            average_queue=avg_q,
            throughput=vehicles_completed,
            vehicles_generated=vehicles_generated,
            vehicles_completed=vehicles_completed,
            emergency_waiting_time=emerg_wait,
            emergency_travel_time=emerg_travel,
            emergency_completed=emerg_completed_flag,
            emergency_response_time=emerg_resp,
            emergency_detected_time=emergency_controller.detected_time,
            emergency_corridor_activated_time=emergency_controller.activated_time,
            emergency_completed_time=emergency_controller.completed_time,
            emergency_intersections_cleared=len(emergency_controller.cleared_intersections),
            emergency_preemption_count=emergency_controller.preemption_count,
            corridor_event_log=[e.to_dict() for e in emergency_controller.event_log],
            normal_vehicles_waiting_time=normal_waiting_time,
            emergency_corridor_enabled=self.enable_emergency_corridor,
            simulation_duration=self.scenario.duration_seconds,
            seed=seed,
            total_person_delay=total_person_delay,
            average_person_delay=avg_person_delay,
            total_passengers_served=total_passengers_served,
            jain_fairness_index=jain_idx,
            max_approach_wait=max_appr_w,
            starvation_violations=starv_violations,
            idle_vehicle_seconds=emissions.idle_vehicle_seconds,
            estimated_fuel_liters=emissions.estimated_fuel_liters,
            estimated_co2_kg=emissions.estimated_co2_kg,
            active_emergencies_count=len(all_emergency_vehs),
            resolved_emergency_conflicts=emergency_controller.total_conflicts_resolved,
            emergency_vehicle_results=emergency_vehicle_results,
            cross_street_person_delay=cross_person_delay,
            cross_street_vehicles=len(cross_all),
        )


def simulate(
    scenario: SimulationScenario,
    signal_plan: Optional[Dict[str, int]] = None,
    seed: Optional[int] = None,
    enable_emergency_corridor: bool = False,
    prepare_lookahead_seconds: int = 3,
    adaptive_controller: Optional[Any] = None,
) -> SimulationMetrics:
    """Convenience functional API to execute traffic simulation.

    Args:
        scenario: SimulationScenario specification.
        signal_plan: Signal timing plan {"I1": 30, ...}.
        seed: Deterministic random seed for arrivals.
        enable_emergency_corridor: If True, activates dynamic green corridor for emergency vehicles.
        prepare_lookahead_seconds: Lookahead seconds for preparing downstream signals.
        adaptive_controller: Optional AdaptiveRollingHorizonController.

    Returns:
        SimulationMetrics: Resulting traffic performance metrics.
    """
    simulator = TrafficSimulator(
        scenario=scenario,
        enable_emergency_corridor=enable_emergency_corridor,
        prepare_lookahead_seconds=prepare_lookahead_seconds,
        adaptive_controller=adaptive_controller,
    )
    return simulator.simulate(signal_plan=signal_plan, seed=seed, adaptive_controller=adaptive_controller)
