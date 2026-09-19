"""Dynamic Real-Time Emergency Green Corridor Controller for QuantumFlow.

Coordinates second-by-second traffic signal preemption, downstream green wave preparation,
multi-emergency conflict arbitration, and automated recovery along active emergency vehicle routes:
1. Emergency Detection: Identifies vehicle arrival, active route, and origin intersection.
2. Multi-Emergency Arbitration: Detects junction conflicts and applies conflict-free schedules.
3. Progressive Preemption: Overrides signals along the route to PREEMPT_ACTIVE (forced green) as the vehicle approaches.
4. Downstream Lookahead: Prepares the subsequent intersection (PREPARE) to ensure smooth transit progression.
5. Clean Localized Release: Returns passed intersections to NORMAL/RECOVERY mode without preempting unrelated nodes.
6. Automatic Recovery: Seamlessly restores normal cyclic signal operation upon emergency completion.
7. Deterministic Event Logging: Records every transition with timestamp and structured metadata.
"""

from typing import Dict, List, Tuple, Optional, Set, Any, Sequence, Union
from simulation.models import Vehicle
from simulation.emergency_events import (
    IntersectionSignalMode,
    EmergencyEventType,
    EmergencyEvent,
)
from optimization.emergency_conflict import (
    EmergencyConflictRequest,
    EmergencyConflictSchedule,
    detect_emergency_conflicts,
    solve_emergency_conflict,
)


class EmergencyCorridorController:
    """Real-time route-aware dynamic emergency green corridor orchestrator."""

    def __init__(
        self,
        network_intersections: Tuple[str, ...] = ("I1", "I2", "I3", "I4"),
        prepare_lookahead_seconds: int = 3,
        enabled: bool = True,
    ):
        self.network_intersections = network_intersections
        self.prepare_lookahead_seconds = prepare_lookahead_seconds
        self.enabled = enabled

        # Active state tracking
        self.is_active: bool = False
        self.active_vehicle_id: Optional[str] = None
        self.active_route: Tuple[str, ...] = ()
        self.active_vehicle_ids: Set[str] = set()
        self.intersection_modes: Dict[str, IntersectionSignalMode] = {
            name: IntersectionSignalMode.NORMAL for name in network_intersections
        }

        # Progress tracking
        self.detected_time: Optional[int] = None
        self.activated_time: Optional[int] = None
        self.completed_time: Optional[int] = None
        self.cleared_intersections: List[str] = []
        self.preemption_counts: Dict[str, int] = {name: 0 for name in network_intersections}
        self.event_log: List[EmergencyEvent] = []

        # Conflict resolution tracking
        self.active_conflict_schedules: Dict[str, EmergencyConflictSchedule] = {}
        self.total_conflicts_detected: int = 0
        self.total_conflicts_resolved: int = 0

        # Internal state history
        self._logged_preemptions: Set[str] = set()
        self._logged_prepares: Set[str] = set()
        self._logged_cleared: Set[str] = set()
        self._detected_vehicles: Set[str] = set()
        self._completed_vehicles: Set[str] = set()

    def validate_route(self, route: Sequence[str]) -> None:
        """Validate emergency corridor route against network topology."""
        if not route:
            raise ValueError("Emergency route cannot be empty.")

        for inter in route:
            if inter not in self.network_intersections:
                raise ValueError(
                    f"Invalid route intersection '{inter}'. Known intersections: {self.network_intersections}."
                )

        indices = [self.network_intersections.index(inter) for inter in route]
        for k in range(len(indices) - 1):
            if indices[k + 1] <= indices[k]:
                raise ValueError(
                    f"Non-forward corridor route transition: {route[k]} -> {route[k+1]}."
                )

    def _log_event(
        self,
        timestamp: int,
        event_type: EmergencyEventType,
        vehicle_id: str,
        intersection: Optional[str] = None,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record structured lifecycle event into the deterministic event log."""
        event = EmergencyEvent(
            timestamp=timestamp,
            event_type=event_type.value,
            vehicle_id=vehicle_id,
            intersection=intersection,
            message=message,
            details=details if details is not None else {},
        )
        self.event_log.append(event)

    def update(
        self,
        second: int,
        active_emergency_vehicle: Optional[Union[Vehicle, Sequence[Vehicle]]] = None,
        transit_pipes: Sequence[Tuple[Vehicle, int, str]] = (),
    ) -> Dict[str, IntersectionSignalMode]:
        """Update second-by-second signal modes based on emergency vehicle positions."""
        if not self.enabled:
            return {name: IntersectionSignalMode.NORMAL for name in self.network_intersections}

        # Normalize active vehicles list
        if active_emergency_vehicle is None:
            active_vehs: List[Vehicle] = []
        elif isinstance(active_emergency_vehicle, Vehicle):
            active_vehs = [active_emergency_vehicle]
        else:
            active_vehs = list(active_emergency_vehicle)

        # Process any vehicles that just completed
        for veh in active_vehs:
            if veh.completed and veh.vehicle_id not in self._completed_vehicles:
                self._completed_vehicles.add(veh.vehicle_id)
                self.completed_time = second
                last_inter = veh.route[-1]
                if last_inter not in self._logged_cleared:
                    self._logged_cleared.add(last_inter)
                    self.cleared_intersections.append(last_inter)
                    self._log_event(
                        timestamp=second,
                        event_type=EmergencyEventType.CLEARED_INTERSECTION,
                        vehicle_id=veh.vehicle_id,
                        intersection=last_inter,
                        message=f"Emergency vehicle '{veh.vehicle_id}' cleared destination intersection '{last_inter}'.",
                    )
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.EMERGENCY_COMPLETED,
                    vehicle_id=veh.vehicle_id,
                    intersection=last_inter,
                    message=f"Emergency vehicle '{veh.vehicle_id}' reached destination '{veh.destination}' at t={second}s.",
                    details={"response_time": second - veh.arrival_time},
                )

        # Filter out completed vehicles
        uncompleted_vehs = [v for v in active_vehs if not v.completed]

        # Case 1: No active uncompleted emergency vehicles in the network
        if not uncompleted_vehs:
            if self.is_active:
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.CORRIDOR_RELEASED,
                    vehicle_id=self.active_vehicle_id or "ALL_EMERG",
                    message="All emergency vehicles completed/absent; releasing corridor preemption.",
                )
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.NORMAL_RESUMED,
                    vehicle_id=self.active_vehicle_id or "ALL_EMERG",
                    message="Normal cyclic signal control resumed on all intersections.",
                )
                self.is_active = False
                self.active_vehicle_id = None
                self.active_route = ()
                self.active_vehicle_ids.clear()

            self.intersection_modes = {
                name: IntersectionSignalMode.NORMAL for name in self.network_intersections
            }
            return self.intersection_modes

        # Case 2: Process newly detected vehicles
        for veh in uncompleted_vehs:
            if veh.vehicle_id not in self._detected_vehicles:
                self.validate_route(veh.route)
                self._detected_vehicles.add(veh.vehicle_id)
                self.active_vehicle_ids.add(veh.vehicle_id)
                if not self.is_active:
                    self.is_active = True
                    self.active_vehicle_id = veh.vehicle_id
                    self.active_route = veh.route
                    self.detected_time = second
                    self.activated_time = second

                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.EMERGENCY_DETECTED,
                    vehicle_id=veh.vehicle_id,
                    intersection=veh.origin,
                    message=f"Emergency vehicle '{veh.vehicle_id}' detected at entry intersection '{veh.origin}'.",
                    details={"route": list(veh.route), "destination": veh.destination},
                )
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.CORRIDOR_ACTIVATED,
                    vehicle_id=veh.vehicle_id,
                    message=f"Dynamic green corridor activated for '{veh.vehicle_id}' along route: {' -> '.join(veh.route)}.",
                    details={"route": list(veh.route)},
                )

        # Reset all intersection modes to NORMAL by default
        new_modes: Dict[str, IntersectionSignalMode] = {
            name: IntersectionSignalMode.NORMAL for name in self.network_intersections
        }

        # Multi-Emergency Conflict Detection
        if len(uncompleted_vehs) >= 2:
            requests = [
                EmergencyConflictRequest(
                    vehicle_id=v.vehicle_id,
                    route=v.route,
                    current_intersection=v.current_intersection or v.origin,
                    distance_to_conflict=len(v.route) - v.current_step,
                    estimated_arrival_at_conflict=second + (len(v.route) - v.current_step) * 2,
                    priority_level=1,
                )
                for v in uncompleted_vehs
            ]
            conflicts = detect_emergency_conflicts(requests)
            for c_inter, c_reqs in conflicts.items():
                if c_inter not in self.active_conflict_schedules:
                    self.total_conflicts_detected += 1
                    sched = solve_emergency_conflict(c_reqs, c_inter, current_time=second)
                    self.active_conflict_schedules[c_inter] = sched
                    self.total_conflicts_resolved += 1
                    self._log_event(
                        timestamp=second,
                        event_type=EmergencyEventType.CORRIDOR_ACTIVATED,
                        vehicle_id=",".join(sched.sequenced_vehicles),
                        intersection=c_inter,
                        message=f"Conflict detected at '{c_inter}'. QUBO resolved priority sequence: {' -> '.join(sched.sequenced_vehicles)}.",
                        details={"schedule": sched.to_dict()},
                    )

        # Apply preemption for each active uncompleted emergency vehicle
        for veh in uncompleted_vehs:
            route = veh.route

            # Transit check
            transit_info = None
            for t_veh, arr_time, next_inter in transit_pipes:
                if t_veh.vehicle_id == veh.vehicle_id:
                    transit_info = (arr_time, next_inter)
                    break

            if transit_info is not None:
                arr_time, next_inter = transit_info
                curr_step = veh.current_step
                prev_inter = route[curr_step] if curr_step < len(route) else None

                if prev_inter and prev_inter not in self._logged_cleared:
                    self._logged_cleared.add(prev_inter)
                    self.cleared_intersections.append(prev_inter)
                    self._log_event(
                        timestamp=second,
                        event_type=EmergencyEventType.CLEARED_INTERSECTION,
                        vehicle_id=veh.vehicle_id,
                        intersection=prev_inter,
                        message=f"Emergency vehicle '{veh.vehicle_id}' cleared intersection '{prev_inter}'; entering transit to '{next_inter}'.",
                    )

                time_to_arrival = arr_time - second
                if time_to_arrival <= self.prepare_lookahead_seconds:
                    new_modes[next_inter] = IntersectionSignalMode.PREEMPT_ACTIVE
                    if next_inter not in self._logged_preemptions:
                        self._logged_preemptions.add(next_inter)
                        self.preemption_counts[next_inter] += 1
                        self._log_event(
                            timestamp=second,
                            event_type=EmergencyEventType.PREEMPTION_ACTIVE,
                            vehicle_id=veh.vehicle_id,
                            intersection=next_inter,
                            message=f"Preemption wave triggered at '{next_inter}' (lookahead {time_to_arrival}s).",
                        )
                else:
                    new_modes[next_inter] = IntersectionSignalMode.PREPARE
                    if next_inter not in self._logged_prepares:
                        self._logged_prepares.add(next_inter)
                        self._log_event(
                            timestamp=second,
                            event_type=EmergencyEventType.PREPARE_DOWNSTREAM,
                            vehicle_id=veh.vehicle_id,
                            intersection=next_inter,
                            message=f"Downstream intersection '{next_inter}' prepared for green wave.",
                        )
            else:
                # Vehicle is queued at an intersection
                curr_inter = veh.current_intersection
                if curr_inter:
                    new_modes[curr_inter] = IntersectionSignalMode.PREEMPT_ACTIVE
                    if curr_inter not in self._logged_preemptions:
                        self._logged_preemptions.add(curr_inter)
                        self.preemption_counts[curr_inter] += 1
                        self._log_event(
                            timestamp=second,
                            event_type=EmergencyEventType.PREEMPTION_ACTIVE,
                            vehicle_id=veh.vehicle_id,
                            intersection=curr_inter,
                            message=f"Signal at '{curr_inter}' preempted for active emergency queue clearance.",
                        )

                    curr_idx = route.index(curr_inter) if curr_inter in route else -1
                    if curr_idx != -1 and curr_idx + 1 < len(route):
                        next_downstream = route[curr_idx + 1]
                        if new_modes[next_downstream] == IntersectionSignalMode.NORMAL:
                            new_modes[next_downstream] = IntersectionSignalMode.PREPARE

        self.intersection_modes = new_modes
        return self.intersection_modes

    def is_signal_green_forced(self, intersection: str) -> bool:
        """Return True if intersection signal is currently forced green by active emergency preemption."""
        if not self.enabled or not self.is_active:
            return False
        return self.intersection_modes.get(intersection) == IntersectionSignalMode.PREEMPT_ACTIVE

    @property
    def preemption_count(self) -> int:
        """Total distinct preemption events triggered across all intersections."""
        return len(self._logged_preemptions)

    @property
    def recovery_completed(self) -> bool:
        """True if the emergency corridor has completed its mission and returned to normal operation."""
        return self.completed_time is not None and not self.is_active
