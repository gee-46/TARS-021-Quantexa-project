"""Dynamic Real-Time Emergency Green Corridor Controller for QuantumFlow.

Coordinates second-by-second traffic signal preemption, downstream green wave preparation,
and automated recovery along active emergency vehicle routes:
1. Emergency Detection: Identifies vehicle arrival, active route, and origin intersection.
2. Progressive Preemption: Overrides signals along the route to PREEMPT_ACTIVE (forced green) as the vehicle approaches.
3. Downstream Lookahead: Prepares the subsequent intersection (PREPARE) to ensure smooth transit progression.
4. Clean Localized Release: Returns passed intersections to NORMAL/RECOVERY mode without preempting unrelated nodes.
5. Automatic Recovery: Seamlessly restores normal cyclic signal operation upon emergency completion.
6. Deterministic Event Logging: Records every transition with timestamp and structured metadata.
"""

from typing import Dict, List, Tuple, Optional, Set, Any, Sequence
from simulation.models import Vehicle
from simulation.emergency_events import (
    IntersectionSignalMode,
    EmergencyEventType,
    EmergencyEvent,
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

        # Internal state history
        self._logged_preemptions: Set[str] = set()
        self._logged_prepares: Set[str] = set()
        self._logged_cleared: Set[str] = set()

    def validate_route(self, route: Sequence[str]) -> None:
        """Validate emergency corridor route against network topology.

        Raises:
            ValueError: If route is empty or contains unknown/non-sequential intersections.
        """
        if not route:
            raise ValueError("Emergency route cannot be empty.")

        for inter in route:
            if inter not in self.network_intersections:
                raise ValueError(
                    f"Invalid route intersection '{inter}'. Known intersections: {self.network_intersections}."
                )

        # Check sequential order along directed line grid
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
        active_emergency_vehicle: Optional[Vehicle],
        transit_pipes: List[Tuple[Vehicle, int, str]],
    ) -> Dict[str, IntersectionSignalMode]:
        """Update corridor signal preemption modes and event log for the current discrete second.

        Args:
            second: Current simulation time step in seconds.
            active_emergency_vehicle: Active emergency Vehicle instance or None.
            transit_pipes: List of vehicles currently traveling between intersections.

        Returns:
            Dict[str, IntersectionSignalMode]: Current operating mode for every network intersection.
        """
        if not self.enabled:
            return {name: IntersectionSignalMode.NORMAL for name in self.network_intersections}

        # Case 1: No active emergency vehicle in the network
        if active_emergency_vehicle is None:
            if self.is_active:
                # Emergency corridor previously active -> release and recover
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.CORRIDOR_RELEASED,
                    vehicle_id=self.active_vehicle_id or "EMERG",
                    message="Emergency vehicle absent; releasing corridor preemption.",
                )
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.NORMAL_RESUMED,
                    vehicle_id=self.active_vehicle_id or "EMERG",
                    message="Normal cyclic signal control resumed on all intersections.",
                )
                self.is_active = False
                self.active_vehicle_id = None
                self.active_route = ()

            self.intersection_modes = {
                name: IntersectionSignalMode.NORMAL for name in self.network_intersections
            }
            return self.intersection_modes

        veh = active_emergency_vehicle
        route = veh.route

        # Case 2: New emergency vehicle detected
        if not self.is_active:
            self.validate_route(route)
            self.is_active = True
            self.active_vehicle_id = veh.vehicle_id
            self.active_route = route
            self.detected_time = second
            self.activated_time = second
            self._logged_preemptions.clear()
            self._logged_prepares.clear()
            self._logged_cleared.clear()

            self._log_event(
                timestamp=second,
                event_type=EmergencyEventType.EMERGENCY_DETECTED,
                vehicle_id=veh.vehicle_id,
                intersection=veh.origin,
                message=f"Emergency vehicle '{veh.vehicle_id}' detected at entry intersection '{veh.origin}'.",
                details={"route": list(route), "destination": veh.destination},
            )
            self._log_event(
                timestamp=second,
                event_type=EmergencyEventType.CORRIDOR_ACTIVATED,
                vehicle_id=veh.vehicle_id,
                message=f"Dynamic green corridor activated along route: {' -> '.join(route)}.",
                details={"route": list(route)},
            )

        # Reset all intersection modes to NORMAL by default
        new_modes: Dict[str, IntersectionSignalMode] = {
            name: IntersectionSignalMode.NORMAL for name in self.network_intersections
        }

        # Case 3: Emergency vehicle reached destination and completed
        if veh.completed:
            self.completed_time = second
            last_inter = route[-1]
            if last_inter not in self._logged_cleared:
                self._logged_cleared.add(last_inter)
                self.cleared_intersections.append(last_inter)
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.CLEARED_INTERSECTION,
                    vehicle_id=veh.vehicle_id,
                    intersection=last_inter,
                    message=f"Emergency vehicle cleared destination intersection '{last_inter}'.",
                )

            self._log_event(
                timestamp=second,
                event_type=EmergencyEventType.EMERGENCY_COMPLETED,
                vehicle_id=veh.vehicle_id,
                intersection=last_inter,
                message=f"Emergency vehicle reached destination '{veh.destination}' at t={second}s.",
                details={"response_time": second - veh.arrival_time},
            )
            self._log_event(
                timestamp=second,
                event_type=EmergencyEventType.CORRIDOR_RELEASED,
                vehicle_id=veh.vehicle_id,
                message="Emergency completed; releasing green corridor.",
            )
            self._log_event(
                timestamp=second,
                event_type=EmergencyEventType.NORMAL_RESUMED,
                vehicle_id=veh.vehicle_id,
                message="Normal cyclic signal control resumed on all intersections.",
            )

            self.is_active = False
            self.intersection_modes = new_modes
            return self.intersection_modes

        # Case 4: Check if vehicle is currently in transit between intersections
        transit_info = None
        for t_veh, arr_time, next_inter in transit_pipes:
            if t_veh.vehicle_id == veh.vehicle_id:
                transit_info = (arr_time, next_inter)
                break

        if transit_info is not None:
            arr_time, next_inter = transit_info
            curr_step = veh.current_step
            prev_inter = route[curr_step] if curr_step < len(route) else None

            # Mark previous intersection cleared
            if prev_inter and prev_inter not in self._logged_cleared:
                self._logged_cleared.add(prev_inter)
                self.cleared_intersections.append(prev_inter)
                self._log_event(
                    timestamp=second,
                    event_type=EmergencyEventType.CLEARED_INTERSECTION,
                    vehicle_id=veh.vehicle_id,
                    intersection=prev_inter,
                    message=f"Emergency vehicle cleared intersection '{prev_inter}'; entering transit to '{next_inter}'.",
                )

            # Lookahead preparation & preemptive green wave on downstream intersection
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
                        message=f"Preempting '{next_inter}' to green for incoming emergency vehicle (arrival in {time_to_arrival}s).",
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
                        message=f"Preparing downstream intersection '{next_inter}' for approaching emergency vehicle.",
                    )

        else:
            # Case 5: Vehicle is queued/waiting at an intersection
            curr_inter = veh.current_intersection
            if curr_inter:
                # Force current intersection to PREEMPT_ACTIVE (green)
                new_modes[curr_inter] = IntersectionSignalMode.PREEMPT_ACTIVE
                if curr_inter not in self._logged_preemptions:
                    self._logged_preemptions.add(curr_inter)
                    self.preemption_counts[curr_inter] += 1
                    self._log_event(
                        timestamp=second,
                        event_type=EmergencyEventType.PREEMPTION_ACTIVE,
                        vehicle_id=veh.vehicle_id,
                        intersection=curr_inter,
                        message=f"Active preemption enabled: forcing intersection '{curr_inter}' green.",
                    )

                # Prepare next downstream intersection on the route
                if not veh.is_at_destination:
                    next_idx = veh.current_step + 1
                    if next_idx < len(route):
                        downstream_inter = route[next_idx]
                        new_modes[downstream_inter] = IntersectionSignalMode.PREPARE
                        if downstream_inter not in self._logged_prepares:
                            self._logged_prepares.add(downstream_inter)
                            self._log_event(
                                timestamp=second,
                                event_type=EmergencyEventType.PREPARE_DOWNSTREAM,
                                vehicle_id=veh.vehicle_id,
                                intersection=downstream_inter,
                                message=f"Downstream intersection '{downstream_inter}' prepared for green corridor transition.",
                            )

        self.intersection_modes = new_modes
        return self.intersection_modes

    def is_signal_green_forced(self, intersection: str) -> bool:
        """True if emergency controller is actively forcing green on the intersection."""
        return self.intersection_modes.get(intersection) == IntersectionSignalMode.PREEMPT_ACTIVE
