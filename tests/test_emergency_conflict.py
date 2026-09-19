"""Unit tests for Multi-Emergency Conflict Detection and QUBO Sequencing.

Tests:
- No conflict single emergency
- Two emergencies arriving at the same junction
- Opposing corridors contending for a shared intersection (e.g. I3)
- Three simultaneous emergencies
- Conflicting green request avoidance (non-overlapping clearance intervals)
- Conflict QUBO formulation and upper-triangular structure
- Solver execution via SA fallback
- Priority scheduling and recovery
- Integration with EmergencyCorridorController
"""

import pytest
import numpy as np
from optimization.emergency_conflict import (
    EmergencyConflictRequest,
    EmergencyConflictSchedule,
    detect_emergency_conflicts,
    build_conflict_qubo,
    solve_emergency_conflict,
)
from simulation.models import Vehicle
from simulation.emergency_controller import EmergencyCorridorController
from simulation.emergency_events import IntersectionSignalMode, EmergencyEventType


def test_no_conflict_single_emergency():
    """Verify single emergency vehicle produces no conflict."""
    req = EmergencyConflictRequest(
        vehicle_id="EMERG_1",
        route=("I1", "I2", "I3"),
        current_intersection="I1",
        distance_to_conflict=2,
        estimated_arrival_at_conflict=10,
    )
    conflicts = detect_emergency_conflicts([req])
    assert len(conflicts) == 0

    # Direct resolution handles single request cleanly
    sched = solve_emergency_conflict([req], conflict_intersection="I3", current_time=0)
    assert sched.conflict_intersection == "I3"
    assert sched.sequenced_vehicles == ["EMERG_1"]
    assert sched.is_feasible is True
    assert "EMERG_1" in sched.clearance_intervals


def test_two_emergencies_same_junction_conflict():
    """Verify conflict detection when two vehicles contend for intersection I3."""
    req1 = EmergencyConflictRequest(
        vehicle_id="EMERG_A",
        route=("I1", "I2", "I3"),
        current_intersection="I1",
        distance_to_conflict=2,
        estimated_arrival_at_conflict=20,
        priority_level=1,
    )
    req2 = EmergencyConflictRequest(
        vehicle_id="EMERG_B",
        route=("I2", "I3", "I4"),
        current_intersection="I2",
        distance_to_conflict=1,
        estimated_arrival_at_conflict=22,
        priority_level=2,
    )

    conflicts = detect_emergency_conflicts([req1, req2], contested_lookahead_seconds=15)
    assert "I3" in conflicts
    assert len(conflicts["I3"]) == 2

    # Solve conflict QUBO
    sched = solve_emergency_conflict([req1, req2], conflict_intersection="I3", current_time=15, clearance_time_seconds=6)
    assert sched.is_feasible is True
    assert set(sched.sequenced_vehicles) == {"EMERG_A", "EMERG_B"}

    # Ensure non-overlapping intervals
    int_a = sched.clearance_intervals["EMERG_A"]
    int_b = sched.clearance_intervals["EMERG_B"]

    # Either A finishes before B starts or B finishes before A starts
    assert int_a[1] <= int_b[0] or int_b[1] <= int_a[0]


def test_three_emergencies_conflict_qubo():
    """Verify 3-vehicle conflict QUBO matrix dimensions and valid permutation sequencing."""
    requests = [
        EmergencyConflictRequest(
            vehicle_id=f"EMERG_{i}",
            route=("I1", "I2", "I3", "I4"),
            current_intersection="I2",
            distance_to_conflict=1,
            estimated_arrival_at_conflict=30 + i * 2,
            priority_level=i + 1,
        )
        for i in range(3)
    ]

    qubo = build_conflict_qubo(requests, conflict_intersection="I3", clearance_time_seconds=5)
    # 3 vehicles x 3 slots = 9 variables -> (9, 9) matrix
    assert qubo.Q.shape == (9, 9)
    assert np.allclose(qubo.Q, np.triu(qubo.Q))

    sched = solve_emergency_conflict(requests, conflict_intersection="I3", current_time=25, clearance_time_seconds=5)
    assert len(sched.sequenced_vehicles) == 3
    assert sched.is_feasible is True

    # Check temporal ordering
    for i in range(len(sched.sequenced_vehicles) - 1):
        v1 = sched.sequenced_vehicles[i]
        v2 = sched.sequenced_vehicles[i + 1]
        assert sched.clearance_intervals[v1][1] <= sched.clearance_intervals[v2][0]


def test_emergency_controller_multi_vehicle_arbitration():
    """Verify EmergencyCorridorController dynamically routes 2 simultaneous emergency vehicles without safety violations."""
    ctrl = EmergencyCorridorController(
        network_intersections=("I1", "I2", "I3", "I4"),
        prepare_lookahead_seconds=3,
        enabled=True,
    )

    v1 = Vehicle(
        vehicle_id="AMB_1",
        origin="I1",
        destination="I3",
        arrival_time=0,
        route=("I1", "I2", "I3"),
        current_step=0,
        is_emergency=True,
    )
    v2 = Vehicle(
        vehicle_id="AMB_2",
        origin="I2",
        destination="I4",
        arrival_time=0,
        route=("I2", "I3", "I4"),
        current_step=0,
        is_emergency=True,
    )

    # Step at t=0
    modes = ctrl.update(second=0, active_emergency_vehicle=[v1, v2], transit_pipes=[])
    assert ctrl.is_active is True
    assert ctrl.total_conflicts_detected >= 1
    assert ctrl.total_conflicts_resolved >= 1

    # Both origin intersections have active green preemption
    assert ctrl.is_signal_green_forced("I1") is True
    assert ctrl.is_signal_green_forced("I2") is True

    # Complete AMB_1
    v1.completed = True
    ctrl.update(second=15, active_emergency_vehicle=[v1, v2], transit_pipes=[])
    assert "I3" in ctrl.cleared_intersections

    # Complete AMB_2
    v2.completed = True
    ctrl.update(second=30, active_emergency_vehicle=[v1, v2], transit_pipes=[])
    assert ctrl.is_active is False
    assert ctrl.recovery_completed is True

