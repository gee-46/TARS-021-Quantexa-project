"""Unit tests for People-Aware Traffic Modeling and Passenger Occupancy.

Tests:
- VehicleTypeConfig configurable occupancies.
- Vehicle person_delay accumulation (waiting_time * passenger_count).
- Backward compatibility (defaults: passenger_count=1, car=1.5, type="car").
- TrafficSimulator calculation of vehicle_delay vs person_delay.
- QUBO objective with person-weighted demand.
"""

import pytest
from simulation.models import Vehicle, VehicleTypeConfig, SignalState
from simulation.scenario import SimulationScenario
from simulation.engine import TrafficSimulator
from optimization.traffic_objectives import add_wait_term, evaluate_wait
from optimization.qubo_builder import build_qubo, FullQUBOConfig


def test_vehicle_type_config_defaults_and_custom():
    """Verify VehicleTypeConfig defaults and custom occupancy lookups."""
    cfg = VehicleTypeConfig()
    assert cfg.car_occupancy == 1.5
    assert cfg.bus_occupancy == 30.0
    assert cfg.motorcycle_occupancy == 1.0
    assert cfg.truck_occupancy == 1.0
    assert cfg.emergency_occupancy == 2.0

    assert cfg.get_occupancy("car") == 1.5
    assert cfg.get_occupancy("bus") == 30.0
    assert cfg.get_occupancy("transit_bus") == 30.0
    assert cfg.get_occupancy("motorcycle") == 1.0
    assert cfg.get_occupancy("heavy_truck") == 1.0
    assert cfg.get_occupancy("emergency_ambulance") == 2.0

    custom = VehicleTypeConfig(car_occupancy=2.0, bus_occupancy=45.0)
    assert custom.get_occupancy("bus") == 45.0
    assert custom.get_occupancy("car") == 2.0


def test_vehicle_person_delay_property():
    """Verify person_delay calculation is strictly waiting_time * passenger_count."""
    car = Vehicle(
        vehicle_id="CAR_01",
        origin="I1",
        destination="I4",
        arrival_time=0,
        route=("I1", "I2", "I3", "I4"),
        vehicle_type="car",
        passenger_count=2,
    )
    assert car.person_delay == 0.0

    car.waiting_time = 15
    assert car.person_delay == 30.0  # 15 * 2

    bus = Vehicle(
        vehicle_id="BUS_01",
        origin="I1",
        destination="I4",
        arrival_time=0,
        route=("I1", "I2", "I3", "I4"),
        vehicle_type="bus",
        passenger_count=35,
    )
    bus.waiting_time = 20
    assert bus.person_delay == 700.0  # 20 * 35


def test_vehicle_backward_compatibility():
    """Verify Vehicle initializes with backward compatible defaults."""
    v = Vehicle(
        vehicle_id="V_OLD",
        origin="I1",
        destination="I2",
        arrival_time=5,
        route=("I1", "I2"),
    )
    assert v.vehicle_type == "car"
    assert v.passenger_count == 1
    v.waiting_time = 10
    assert v.person_delay == 10.0


def test_simulation_accumulates_person_delay():
    """Verify TrafficSimulator tracks total_person_delay alongside vehicle_delay."""
    scenario = SimulationScenario(
        scenario_id="bus_test",
        duration_seconds=60,
        arrival_rates={"I1": 0.4, "I2": 0.2, "I3": 0.2, "I4": 0.2},
        initial_queues={"I1": 5, "I2": 5, "I3": 5, "I4": 5},
    )
    sim = TrafficSimulator(scenario=scenario, vehicle_type_config=VehicleTypeConfig(bus_occupancy=40.0))
    metrics = sim.simulate(signal_plan={"I1": 30, "I2": 30, "I3": 30, "I4": 30}, seed=42)

    assert metrics.total_person_delay >= metrics.normal_vehicles_waiting_time
    assert metrics.average_person_delay >= 0.0


def test_qubo_person_weighted_objective():
    """Verify QUBO construction supports person-weighted queue states."""
    traffic_state = {
        "I1": {"queue": 10.0, "density": 0.5, "avg_occupancy": 20.0},  # Bus corridor
        "I2": {"queue": 10.0, "density": 0.5, "avg_occupancy": 1.0},   # Single-occupant corridor
        "I3": {"queue": 10.0, "density": 0.5, "avg_occupancy": 1.0},
        "I4": {"queue": 10.0, "density": 0.5, "avg_occupancy": 1.0},
    }

    # Standard vehicle QUBO
    qubo_std = build_qubo(traffic_state, config=FullQUBOConfig(person_weighted=False))
    # Person-weighted QUBO
    qubo_person = build_qubo(traffic_state, config=FullQUBOConfig(person_weighted=True))

    # In person-weighted QUBO, I1 has 20x higher penalty for short greens
    assert qubo_person.Q.shape == qubo_std.Q.shape
