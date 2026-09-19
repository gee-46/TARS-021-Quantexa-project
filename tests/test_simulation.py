"""Unit tests for Phase 14: 4-Intersection Traffic Simulator and Benchmark Integration."""

import unittest
import numpy as np

from simulation.models import Vehicle, SignalState
from simulation.scenario import (
    SimulationScenario,
    EmergencyVehicleConfig,
    create_default_simulation_scenario,
)
from simulation.metrics import SimulationMetrics
from simulation.engine import TrafficSimulator, simulate
from optimization.controllers import FixedTimeController
from optimization.benchmark import (
    create_deterministic_scenario,
    run_benchmark,
)


class TestTrafficSimulation(unittest.TestCase):
    """Test suite for discrete microscopic traffic simulator and its benchmark integration."""

    def setUp(self):
        self.default_plan = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}

    # TEST 1: Deterministic hand-check scenario
    def test_hand_verifiable_scenario(self):
        """Verify analytical hand-verifiable vehicle trajectory on simple network.

        Setup:
            - Duration: 20s
            - 1 vehicle at t=0 at I1.
            - Travel time between intersections: 2s.
            - Service rate: 1 veh/s.
            - Green duration: 45s everywhere (all signals green).

        Expected Trace:
            - t=0: I1 green -> served, enters transit to I2 (arr_t = 2).
            - t=2: arrives I2, green -> served, enters transit to I3 (arr_t = 4).
            - t=4: arrives I3, green -> served, enters transit to I4 (arr_t = 6).
            - t=6: arrives I4, destination -> served at t=6 -> completed!
            - Total waiting time = 0.
            - Travel time = 6.
            - Throughput = 1.
        """
        scenario = SimulationScenario(
            scenario_id="hand_check",
            duration_seconds=20,
            cycle_length=60,
            intersections=("I1", "I2", "I3", "I4"),
            service_rate=1.0,
            travel_time_between_intersections=2,
            arrival_rates={},
            initial_queues={"I1": 1, "I2": 0, "I3": 0, "I4": 0},
        )

        plan = {"I1": 45, "I2": 45, "I3": 45, "I4": 45}
        metrics = simulate(scenario, plan, seed=42)

        self.assertEqual(metrics.throughput, 1)
        self.assertEqual(metrics.vehicles_generated, 1)
        self.assertEqual(metrics.vehicles_completed, 1)
        self.assertEqual(metrics.total_waiting_time, 0.0)
        self.assertEqual(metrics.average_waiting_time, 0.0)

    # TEST 2: Emergency scenario tracking
    def test_emergency_vehicle_tracking(self):
        """Verify emergency vehicle is tracked independently and metrics are calculated."""
        scenario = SimulationScenario(
            scenario_id="emerg_check",
            duration_seconds=30,
            cycle_length=60,
            intersections=("I1", "I2", "I3", "I4"),
            service_rate=1.0,
            travel_time_between_intersections=2,
            arrival_rates={},
            initial_queues={"I1": 0, "I2": 0, "I3": 0, "I4": 0},
            emergency_config=EmergencyVehicleConfig(
                vehicle_id="EMERG_01",
                arrival_time=5,
                route=("I2", "I3", "I4"),
            ),
        )

        plan = {"I1": 45, "I2": 45, "I3": 45, "I4": 45}
        metrics = simulate(scenario, plan, seed=42)

        self.assertTrue(metrics.emergency_completed)
        self.assertEqual(metrics.emergency_waiting_time, 0.0)
        # Entry at t=5 (I2), arrives I3 at t=7, arrives I4 at t=9 -> completes at t=9 -> resp time = 4.0
        self.assertEqual(metrics.emergency_response_time, 4.0)
        self.assertEqual(metrics.emergency_travel_time, 4.0)

    # TEST 3: Reproducibility
    def test_simulation_reproducibility(self):
        """Verify identical seed produces strictly identical vehicle counts, queues, and metrics."""
        scenario = create_default_simulation_scenario(duration_seconds=100)

        m1 = simulate(scenario, self.default_plan, seed=42)
        m2 = simulate(scenario, self.default_plan, seed=42)

        self.assertEqual(m1.vehicles_generated, m2.vehicles_generated)
        self.assertEqual(m1.throughput, m2.throughput)
        self.assertAlmostEqual(m1.total_waiting_time, m2.total_waiting_time)
        self.assertAlmostEqual(m1.average_waiting_time, m2.average_waiting_time)
        self.assertEqual(m1.max_queue, m2.max_queue)
        self.assertAlmostEqual(m1.average_queue, m2.average_queue)
        self.assertEqual(m1.emergency_completed, m2.emergency_completed)

    # TEST 4: Signal plan comparison (Plan A 15s vs Plan B 45s)
    def test_signal_plan_comparison_measurable_difference(self):
        """Verify differing signal allocations produce measurable operational differences."""
        scenario = SimulationScenario(
            scenario_id="compare_plans",
            duration_seconds=120,
            cycle_length=60,
            arrival_rates={"I1": 0.5, "I2": 0.3},
            initial_queues={"I1": 15, "I2": 15, "I3": 10, "I4": 10},
        )

        plan_short = {"I1": 15, "I2": 15, "I3": 15, "I4": 15}
        plan_long = {"I1": 45, "I2": 45, "I3": 45, "I4": 45}

        m_short = simulate(scenario, plan_short, seed=42)
        m_long = simulate(scenario, plan_long, seed=42)

        # Longer green should allow more throughput and lower queue backlog under heavy arrivals
        self.assertGreater(m_long.throughput, m_short.throughput)
        self.assertLess(m_long.total_waiting_time, m_short.total_waiting_time)

    # TEST 5: Signal plan validation
    def test_signal_plan_validation_errors(self):
        """Verify invalid durations or missing intersections raise ValueError."""
        scenario = create_default_simulation_scenario()

        # Missing intersection
        with self.assertRaises(ValueError):
            simulate(scenario, {"I1": 30, "I2": 30, "I3": 30})

        # Invalid duration
        with self.assertRaises(ValueError):
            simulate(scenario, {"I1": 30, "I2": 25, "I3": 30, "I4": 30})

    # TEST 6: Bridge to TrafficMetrics
    def test_metrics_bridge_to_traffic_metrics(self):
        """Verify SimulationMetrics translates to TrafficMetrics with available=True."""
        scenario = create_default_simulation_scenario(duration_seconds=50)
        m = simulate(scenario, self.default_plan, seed=42)

        tm = m.to_traffic_metrics()
        self.assertTrue(tm.available)
        self.assertEqual(tm.total_waiting_time, m.total_waiting_time)
        self.assertEqual(tm.throughput, float(m.throughput))
        self.assertEqual(tm.max_queue, float(m.max_queue))

    # TEST 7: Integration with run_benchmark
    def test_benchmark_runner_with_simulation(self):
        """Verify run_benchmark populates traffic metrics when simulation_scenario is present."""
        scen = create_deterministic_scenario(scenario_id="scen_sim_test", seed=42, with_simulation=True)
        self.assertIsNotNone(scen.simulation_scenario)

        ctrl = FixedTimeController(name="fixed_30")
        results = run_benchmark([scen], [ctrl], num_trials=2, base_seed=42)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.traffic_metrics.available)
            self.assertIsNotNone(r.traffic_metrics.total_waiting_time)
            self.assertIsNotNone(r.traffic_metrics.throughput)
            self.assertGreater(r.traffic_metrics.throughput, 0)


if __name__ == "__main__":
    unittest.main()
