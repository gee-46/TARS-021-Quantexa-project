"""Unit tests for Pareto Multi-Objective Trade-Off Analysis.

Tests:
- ParetoPoint dataclass and serialization.
- ParetoFrontier collection and structure.
- sweep_pareto_frontier execution across lambda values.
- Multi-objective metric recording across emergency prioritization levels.
"""

import pytest
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from optimization.pareto import (
    ParetoPoint,
    ParetoFrontier,
    sweep_pareto_frontier,
)


def test_pareto_point_and_frontier_serialization():
    """Verify ParetoPoint and ParetoFrontier serialize to clean JSON-compatible dictionaries."""
    pt = ParetoPoint(
        lambda_param=0.5,
        emergency_response_time=25.0,
        emergency_waiting_time=2.0,
        civilian_waiting_time=120.0,
        person_delay=180.0,
        throughput=45,
        jain_fairness_index=0.88,
        estimated_co2_kg=0.075,
        qubo_energy=-15.0,
        signal_plan={"I1": 30, "I2": 45, "I3": 45, "I4": 30},
        solver_used="qaoa",
    )
    d = pt.to_dict()
    assert d["lambda_param"] == 0.5
    assert d["solver_used"] == "qaoa"
    assert d["signal_plan"]["I2"] == 45

    frontier = ParetoFrontier(points=[pt], scenario_id="scenario_d", seed=42)
    fd = frontier.to_dict()
    assert fd["scenario_id"] == "scenario_d"
    assert fd["seed"] == 42
    assert len(fd["points"]) == 1


def test_sweep_pareto_frontier_execution():
    """Verify sweep_pareto_frontier executes across specified lambda values."""
    scenario = SimulationScenario(
        scenario_id="pareto_test",
        duration_seconds=30,
        arrival_rates={"I1": 0.3, "I2": 0.2, "I3": 0.1},
        initial_queues={"I1": 5, "I2": 5, "I3": 5, "I4": 5},
        emergency_config=EmergencyVehicleConfig(
            vehicle_id="AMB_PARETO",
            arrival_time=5,
            route=("I2", "I3", "I4"),
        ),
    )

    frontier = sweep_pareto_frontier(
        scenario=scenario,
        lambda_values=(0.0, 0.5, 1.0),
        seed=42,
        qaoa_p=1,
        qaoa_shots=100,
    )

    assert isinstance(frontier, ParetoFrontier)
    assert len(frontier.points) == 3
    assert [p.lambda_param for p in frontier.points] == [0.0, 0.5, 1.0]

    for pt in frontier.points:
        assert pt.throughput >= 0
        assert pt.civilian_waiting_time >= 0.0
        assert pt.person_delay >= 0.0
        assert 0.0 <= pt.jain_fairness_index <= 1.0
        assert pt.estimated_co2_kg >= 0.0
