"""Discrete-Time Microscopic Traffic Simulation Engine for 4-Intersection Grid.

Executes second-by-second traffic progression through network queues and signal phases:
- Queues at I1, I2, I3, I4.
- Cyclic green/red signal operation based on allocated durations (15s, 30s, 45s).
- Deterministic Poisson / scheduled arrivals from seed.
- Intersection-to-intersection transit pipelines.
- Dynamic route-aware Emergency Green Corridor and signal preemption overrides.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import numpy as np

from simulation.models import Vehicle, SignalState
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from simulation.metrics import SimulationMetrics
from simulation.emergency_controller import EmergencyCorridorController
from simulation.emergency_events import EmergencyEventType


class TrafficSimulator:
    """Deterministic, discrete-time microscopic traffic simulator for 4-intersection networks."""

    def __init__(
        self,
        scenario: SimulationScenario,
        enable_emergency_corridor: bool = False,
        prepare_lookahead_seconds: int = 3,
    ):
        self.scenario = scenario
        self.enable_emergency_corridor = enable_emergency_corridor
        self.prepare_lookahead_seconds = prepare_lookahead_seconds
        self.last_emergency_controller: Optional[EmergencyCorridorController] = None

    def simulate(
        self,
        signal_plan: Dict[str, int],
        seed: Optional[int] = None,
    ) -> SimulationMetrics:
        """Run discrete-time simulation of traffic flow under the specified signal plan.

        Args:
            signal_plan: Map of intersection ID to green duration {"I1": 30, ...}.
            seed: Deterministic random seed for arrival realization.

        Returns:
            SimulationMetrics: Measured traffic performance outcomes.
        """
        self.scenario.validate_plan(signal_plan)
        signal_state = SignalState(plan=signal_plan, cycle_length=self.scenario.cycle_length)
        rng = np.random.RandomState(seed if seed is not None else 42)

        # Initialize emergency corridor controller
        emergency_controller = EmergencyCorridorController(
            network_intersections=self.scenario.intersections,
            prepare_lookahead_seconds=self.prepare_lookahead_seconds,
            enabled=self.enable_emergency_corridor,
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
        active_emergency_veh: Optional[Vehicle] = None
        all_emergency_vehs: List[Vehicle] = []

        veh_counter = 0

        # 1. Initialize initial queues at t=0
        for inter_name, count in self.scenario.initial_queues.items():
            if inter_name not in inter_to_idx:
                continue
            start_idx = inter_to_idx[inter_name]
            route = intersections[start_idx:]
            for _ in range(count):
                veh_counter += 1
                v = Vehicle(
                    vehicle_id=f"INIT_{veh_counter:04d}",
                    origin=inter_name,
                    destination=intersections[-1],
                    arrival_time=0,
                    route=route,
                    current_step=0,
                    is_emergency=False,
                )
                queues[inter_name].append(v)
                all_vehicles.append(v)

        # 2. Discrete Time Step Simulation Loop
        for t in range(self.scenario.duration_seconds):
            # A. Check scheduled emergency vehicle arrival
            if (
                self.scenario.emergency_config is not None
                and t == self.scenario.emergency_config.arrival_time
            ):
                e_cfg = self.scenario.emergency_config
                if active_emergency_veh is not None and not active_emergency_veh.completed:
                    # Single active emergency vehicle policy: log rejection if already busy
                    emergency_controller._log_event(
                        timestamp=t,
                        event_type=EmergencyEventType.EMERGENCY_REJECTED_BUSY,
                        vehicle_id=e_cfg.vehicle_id,
                        intersection=e_cfg.route[0],
                        message=f"Emergency vehicle '{e_cfg.vehicle_id}' rejected; corridor busy with '{active_emergency_veh.vehicle_id}'.",
                    )
                else:
                    e_veh = Vehicle(
                        vehicle_id=e_cfg.vehicle_id,
                        origin=e_cfg.route[0],
                        destination=e_cfg.route[-1],
                        arrival_time=t,
                        route=e_cfg.route,
                        current_step=0,
                        is_emergency=True,
                    )
                    queues[e_cfg.route[0]].append(e_veh)
                    all_vehicles.append(e_veh)
                    all_emergency_vehs.append(e_veh)
                    active_emergency_veh = e_veh

            # B. Spawn Poisson new vehicle arrivals at entrance intersections
            for entrance, rate in self.scenario.arrival_rates.items():
                if entrance in inter_to_idx and rate > 0:
                    start_idx = inter_to_idx[entrance]
                    route = intersections[start_idx:]
                    n_arrivals = rng.poisson(lam=rate)
                    for _ in range(n_arrivals):
                        veh_counter += 1
                        v = Vehicle(
                            vehicle_id=f"VEH_{veh_counter:05d}",
                            origin=entrance,
                            destination=intersections[-1],
                            arrival_time=t,
                            route=route,
                            current_step=0,
                            is_emergency=False,
                        )
                        queues[entrance].append(v)
                        all_vehicles.append(v)

            # C. Update dynamic emergency corridor controller
            current_active_emerg = active_emergency_veh if (active_emergency_veh is not None and not active_emergency_veh.completed) else None
            emergency_controller.update(
                second=t,
                active_emergency_vehicle=current_active_emerg,
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

            # E. Service vehicles at intersections where signal is green (normal or emergency forced)
            for inter_name in intersections:
                is_normal_green = signal_state.is_green(inter_name, t)
                is_forced_green = emergency_controller.is_signal_green_forced(inter_name)
                is_green = is_normal_green or is_forced_green

                if is_green and len(queues[inter_name]) > 0:
                    # Serve up to service_rate vehicles per green second
                    capacity = int(self.scenario.service_rate)
                    served_count = min(capacity, len(queues[inter_name]))
                    for _ in range(served_count):
                        veh = queues[inter_name].pop(0)
                        if veh.is_at_destination:
                            # Vehicle reaches destination and exits
                            veh.completed = True
                            veh.completion_time = t
                            completed_vehicles.append(veh)
                            if veh.is_emergency and veh == active_emergency_veh:
                                # Trigger completion update in controller immediately
                                emergency_controller.update(
                                    second=t,
                                    active_emergency_vehicle=veh,
                                    transit_pipes=transit_pipes,
                                )
                        else:
                            # Vehicle moves into downstream transit
                            next_inter = veh.route[veh.current_step + 1]
                            arr_t = t + self.scenario.travel_time_between_intersections
                            transit_pipes.append((veh, arr_t, next_inter))

            # F. Update vehicle waiting and travel time metrics
            for q_list in queues.values():
                for v in q_list:
                    v.waiting_time += 1

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

        all_queue_counts = [count for snap in queue_history for count in snap.values()]
        max_q = max(all_queue_counts) if all_queue_counts else 0
        avg_q = float(np.mean([sum(snap.values()) for snap in queue_history])) if queue_history else 0.0

        primary_emerg = all_emergency_vehs[0] if all_emergency_vehs else None
        emerg_wait: Optional[float] = None
        emerg_travel: Optional[float] = None
        emerg_comp: bool = False
        emerg_resp: Optional[float] = None

        if primary_emerg is not None:
            emerg_wait = float(primary_emerg.waiting_time)
            emerg_travel = float(primary_emerg.travel_time)
            emerg_comp = primary_emerg.completed
            if primary_emerg.completed and primary_emerg.completion_time is not None:
                emerg_resp = float(primary_emerg.completion_time - primary_emerg.arrival_time)

        total_preemptions = sum(emergency_controller.preemption_counts.values())
        raw_events = [ev.to_dict() for ev in emergency_controller.event_log]

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
            emergency_completed=emerg_comp,
            emergency_response_time=emerg_resp,
            emergency_detected_time=emergency_controller.detected_time,
            emergency_corridor_activated_time=emergency_controller.activated_time,
            emergency_completed_time=emergency_controller.completed_time,
            emergency_intersections_cleared=len(emergency_controller.cleared_intersections),
            emergency_preemption_count=total_preemptions,
            corridor_event_log=raw_events,
            normal_vehicles_waiting_time=normal_waiting_time,
            emergency_corridor_enabled=self.enable_emergency_corridor,
            simulation_duration=self.scenario.duration_seconds,
            seed=seed,
        )


def simulate(
    scenario: SimulationScenario,
    signal_plan: Dict[str, int],
    seed: Optional[int] = None,
    enable_emergency_corridor: bool = False,
    prepare_lookahead_seconds: int = 3,
) -> SimulationMetrics:
    """Convenience functional API to execute traffic simulation.

    Args:
        scenario: SimulationScenario specification.
        signal_plan: Signal timing plan {"I1": 30, ...}.
        seed: Deterministic random seed for arrivals.
        enable_emergency_corridor: If True, activates dynamic green corridor for emergency vehicles.
        prepare_lookahead_seconds: Lookahead seconds for preparing downstream signals.

    Returns:
        SimulationMetrics: Resulting traffic performance metrics.
    """
    simulator = TrafficSimulator(
        scenario=scenario,
        enable_emergency_corridor=enable_emergency_corridor,
        prepare_lookahead_seconds=prepare_lookahead_seconds,
    )
    return simulator.simulate(signal_plan=signal_plan, seed=seed)
