"""Unit tests for Fairness Modeling, Jain's Index, and Starvation Penalties.

Tests:
- Jain's Fairness Index mathematical properties:
  - Identical values -> 1.0
  - All zeros -> 1.0 (trivially fair)
  - Extreme inequality -> approaches 1/n
  - Exact manual formula validation: (sum(x))^2 / (n * sum(x^2))
- Starvation penalty in QUBO objective:
  - penalizes shorter green durations when approach exceeds max_wait_cap
- TrafficSimulator tracking of approach delays and starvation violations.
"""

import pytest
import numpy as np
from optimization.traffic_objectives import (
    calculate_jain_fairness_index,
    TrafficObjectiveConfig,
    TrafficState,
    add_starvation_fairness_term,
    evaluate_starvation_fairness,
)
from optimization.qubo_builder import build_qubo, FullQUBOConfig
from simulation.scenario import SimulationScenario
from simulation.engine import TrafficSimulator


def test_jain_fairness_index_mathematical_properties():
    """Verify Jain's fairness index obeys theoretical bounds and edge cases."""
    # 1. Equal distribution -> 1.0
    assert np.isclose(calculate_jain_fairness_index([10.0, 10.0, 10.0, 10.0]), 1.0)
    assert np.isclose(calculate_jain_fairness_index([50.0, 50.0]), 1.0)

    # 2. All zeros -> 1.0 (empty queue / zero delay)
    assert np.isclose(calculate_jain_fairness_index([0.0, 0.0, 0.0, 0.0]), 1.0)
    assert np.isclose(calculate_jain_fairness_index([]), 1.0)

    # 3. 4 users, only 1 served -> 1/4 = 0.25
    assert np.isclose(calculate_jain_fairness_index([100.0, 0.0, 0.0, 0.0]), 0.25)

    # 4. Manual calculation test: values = [2, 4, 4, 6]
    # sum = 16, sum^2 = 256
    # sum_sq = 4 + 16 + 16 + 36 = 72
    # n * sum_sq = 4 * 72 = 288
    # Jain = 256 / 288 = 8 / 9 ≈ 0.8888888888888888
    manual_expected = 256.0 / (4.0 * 72.0)
    assert np.isclose(calculate_jain_fairness_index([2.0, 4.0, 4.0, 6.0]), manual_expected)


def test_starvation_penalty_in_qubo():
    """Verify starvation penalty penalizes 15s green more than 45s green for starved node."""
    traffic_state = TrafficState(
        queues={"I1": 10.0, "I2": 10.0, "I3": 10.0, "I4": 10.0},
        densities={"I1": 0.5, "I2": 0.5, "I3": 0.5, "I4": 0.5},
        approach_waiting_times={"I1": 150.0, "I2": 20.0, "I3": 20.0, "I4": 20.0},  # I1 starved > 120s
    )

    cfg = TrafficObjectiveConfig(starvation_penalty_weight=5.0, max_wait_cap=120.0)

    # Bitstring assigning 15s to I1 (index 0) vs 45s to I1 (index 2)
    x_15 = [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]  # I1=15s
    x_45 = [0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0]  # I1=45s

    pen_15 = evaluate_starvation_fairness(x_15, traffic_state, cfg)
    pen_45 = evaluate_starvation_fairness(x_45, traffic_state, cfg)

    # Shortage for 15s is (45 - 15) = 30; shortage for 45s is 0
    assert pen_15 > pen_45
    assert np.isclose(pen_45, 0.0)


def test_simulation_tracks_starvation_and_fairness():
    """Verify TrafficSimulator computes max_approach_wait and jain_fairness_index."""
    scenario = SimulationScenario(
        scenario_id="starvation_test",
        duration_seconds=60,
        arrival_rates={"I1": 0.5, "I2": 0.2, "I3": 0.2, "I4": 0.2},
        initial_queues={"I1": 15, "I2": 2, "I3": 2, "I4": 2},
    )
    sim = TrafficSimulator(scenario=scenario)
    metrics = sim.simulate(signal_plan={"I1": 15, "I2": 45, "I3": 45, "I4": 45}, seed=42)

    assert 0.0 < metrics.jain_fairness_index <= 1.0
    assert metrics.max_approach_wait >= 0.0
    assert isinstance(metrics.starvation_violations, int)
