"""Simulation Entities and Data Models for Traffic Network.

Provides lightweight structures for:
1. Vehicle: Individual vehicle tracking (entry, waiting, travel times, route progress, vehicle types, passenger occupancy, emergency status).
2. VehicleTypeConfig: Configurable passenger occupancy for cars, buses, motorcycles, trucks, and emergency vehicles.
3. SignalState: Periodic cyclic traffic light phase evaluator for discrete-time steps.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List, Sequence
import numpy as np


@dataclass(frozen=True)
class VehicleTypeConfig:
    """Configurable passenger occupancy mapping for diverse vehicle types.

    Attributes:
        car_occupancy: Average passenger count for passenger cars.
        bus_occupancy: Average passenger count for transit buses.
        motorcycle_occupancy: Average passenger count for motorcycles.
        truck_occupancy: Average passenger count for freight trucks.
        emergency_occupancy: Average crew count for emergency response vehicles.
    """

    car_occupancy: float = 1.5
    bus_occupancy: float = 30.0
    motorcycle_occupancy: float = 1.0
    truck_occupancy: float = 1.0
    emergency_occupancy: float = 2.0

    def get_occupancy(self, vehicle_type: str) -> float:
        """Return nominal passenger count for a given vehicle type string."""
        vt = str(vehicle_type).lower()
        if "bus" in vt:
            return self.bus_occupancy
        elif "moto" in vt:
            return self.motorcycle_occupancy
        elif "truck" in vt:
            return self.truck_occupancy
        elif "emerg" in vt:
            return self.emergency_occupancy
        return self.car_occupancy


@dataclass
class Vehicle:
    """Lightweight vehicle entity progressing through discrete intersection queues.

    Attributes:
        vehicle_id: Unique string identifier.
        origin: Entry intersection ID.
        destination: Exit intersection ID.
        arrival_time: Discrete second when vehicle entered the simulation network.
        route: Sequence of intersection IDs to traverse (e.g. ("I1", "I2", "I3", "I4")).
        current_step: Current index in route sequence (0 to len(route)-1).
        waiting_time: Total seconds spent waiting in queues at red/blocked signals.
        travel_time: Total seconds from arrival to current time (or completion).
        is_emergency: True if this is a priority emergency vehicle.
        completed: True if vehicle reached destination and exited the network.
        completion_time: Discrete second when vehicle exited (or None).
        vehicle_type: Categorical vehicle type ("car", "bus", "motorcycle", "truck", "emergency").
        passenger_count: Number of human occupants in this vehicle (defaults to 1).
        priority_level: Emergency priority tier (1 = most urgent); ignored for civilian vehicles.
    """

    vehicle_id: str
    origin: str
    destination: str
    arrival_time: int
    route: Tuple[str, ...]
    current_step: int = 0
    waiting_time: int = 0
    travel_time: int = 0
    is_emergency: bool = False
    completed: bool = False
    completion_time: Optional[int] = None
    vehicle_type: str = "car"
    passenger_count: int = 1
    priority_level: int = 1

    @property
    def person_delay(self) -> float:
        """Total person-seconds of delay accumulated by all occupants in this vehicle."""
        return float(self.waiting_time * self.passenger_count)

    @property
    def current_intersection(self) -> Optional[str]:
        """Intersection currently being traversed or queued at."""
        if self.current_step < len(self.route):
            return self.route[self.current_step]
        return None

    @property
    def is_at_destination(self) -> bool:
        """True if vehicle is at the final intersection of its route."""
        return self.current_step >= len(self.route) - 1


@dataclass(frozen=True)
class SignalState:
    """Cyclic signal state evaluator for a set of intersection green durations.

    Signal Operation:
        In a repeating cycle of length C (default 60s or 90s), intersection i has green light
        during second t if (t % C) < G_i, where G_i in {15, 30, 45} is the allocated duration.
    """

    plan: Dict[str, int]
    cycle_length: int = 60

    def __post_init__(self) -> None:
        """Validate signal plan format and allowed durations."""
        valid_durations = {15, 30, 45}
        for inter, dur in self.plan.items():
            if dur not in valid_durations:
                raise ValueError(
                    f"Invalid green duration {dur}s for intersection '{inter}'. Allowed: {valid_durations}."
                )

    def is_green(self, intersection: str, second: int) -> bool:
        """Check if intersection signal is green at the given discrete second."""
        green_duration = self.plan.get(intersection, 30)
        cycle_pos = second % self.cycle_length
        return cycle_pos < green_duration
