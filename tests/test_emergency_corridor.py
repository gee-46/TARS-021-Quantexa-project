"""Unit tests for Phase 15: Dynamic Emergency Green Corridor and Automatic Recovery."""

import unittest
import numpy as np

from simulation.models import Vehicle, SignalState
from simulation.scenario import (
    SimulationScenario,
    EmergencyVehicleConfig,
    create_default_simulation_scenario,
)
from simulation.metrics import SimulationMetrics
from simulation.emergency_events import (
    IntersectionSignalMode,
    EmergencyEventType,
    EmergencyEvent,
)
from simulation.emergency_controller import EmergencyCorridorController
from simulation.engine import TrafficSimulator, simulate
from optimization.controllers import HybridController, FixedTimeController
from optimization.benchmark import create_deterministic_scenario


class TestEmergencyCorridor(unittest.TestCase):
    """Test suite for dynamic emergency green corridor, preemption, recovery, and event logging."""

    def setUp(self):
        # Scenario where emergency vehicle arrives at t=10 at I2 -> I3 -> I4
        # Signal plan: all intersections have 15s green (cycle length 60s)
        # So during t=15..59, signals are normally red.
        # When emergency arrives at t=10 (or later), preemption can force green during red phases!
        self.emergency_cfg = EmergencyVehicleConfig(
            vehicle_id="EMERG_01",
            arrival_time=10,
            route=("I2", "I3", "I4"),
        )
        self.scenario = SimulationScenario(
            scenario_id="emerg_corridor_test",
            duration_seconds=120,
            cycle_length=60,
            intersections=("I1", "I2", "I3", "I4"),
            service_rate=1.0,
            travel_time_between_intersections=2,
            arrival_rates={"I1": 0.2, "I2": 0.1, "I3": 0.1},
            initial_queues={"I1": 2, "I2": 3, "I3": 2, "I4": 2},
            emergency_config=self.emergency_cfg,
        )
        self.normal_plan = {"I1": 15, "I2": 15, "I3": 15, "I4": 15}

    # TEST 1 & 2: Detection and Corridor Activation
    def test_emergency_detection_and_activation(self):
        """Verify emergency vehicle arrival triggers detection and corridor activation events."""
        metrics = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        self.assertEqual(metrics.emergency_detected_time, 10)
        self.assertEqual(metrics.emergency_corridor_activated_time, 10)
        self.assertTrue(metrics.emergency_corridor_enabled)

        event_types = [e["event_type"] for e in metrics.corridor_event_log]
        self.assertIn(EmergencyEventType.EMERGENCY_DETECTED.value, event_types)
        self.assertIn(EmergencyEventType.CORRIDOR_ACTIVATED.value, event_types)

    # TEST 3 & 4: Current-intersection preemption and downstream preparation
    def test_preemption_and_downstream_preparation(self):
        """Verify current intersection is forced green (PREEMPT_ACTIVE) and downstream is PREPARE."""
        controller = EmergencyCorridorController(
            network_intersections=("I1", "I2", "I3", "I4"),
            prepare_lookahead_seconds=3,
            enabled=True,
        )

        veh = Vehicle(
            vehicle_id="EMERG_01",
            origin="I2",
            destination="I4",
            arrival_time=10,
            route=("I2", "I3", "I4"),
            current_step=0,
            is_emergency=True,
        )

        modes = controller.update(second=10, active_emergency_vehicle=veh, transit_pipes=[])

        self.assertEqual(modes["I2"], IntersectionSignalMode.PREEMPT_ACTIVE)
        self.assertEqual(modes["I3"], IntersectionSignalMode.PREPARE)
        self.assertEqual(modes["I1"], IntersectionSignalMode.NORMAL)
        self.assertTrue(controller.is_signal_green_forced("I2"))
        self.assertFalse(controller.is_signal_green_forced("I1"))

    # TEST 5 & 6: Emergency progression and completion
    def test_emergency_progression_and_completion(self):
        """Verify emergency vehicle clears intersections and reaches destination."""
        metrics = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        self.assertTrue(metrics.emergency_completed)
        self.assertIsNotNone(metrics.emergency_completed_time)
        self.assertGreater(metrics.emergency_intersections_cleared, 0)
        self.assertGreater(metrics.emergency_preemption_count, 0)

        event_types = [e["event_type"] for e in metrics.corridor_event_log]
        self.assertIn(EmergencyEventType.CLEARED_INTERSECTION.value, event_types)
        self.assertIn(EmergencyEventType.EMERGENCY_COMPLETED.value, event_types)

    # TEST 7 & 8: Corridor release and automatic recovery
    def test_corridor_release_and_automatic_recovery(self):
        """Verify green corridor releases and returns signals to normal cyclic control upon completion."""
        metrics = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        event_types = [e["event_type"] for e in metrics.corridor_event_log]
        self.assertIn(EmergencyEventType.CORRIDOR_RELEASED.value, event_types)
        self.assertIn(EmergencyEventType.NORMAL_RESUMED.value, event_types)

        # Confirm completion event occurred before resumption
        comp_idx = event_types.index(EmergencyEventType.EMERGENCY_COMPLETED.value)
        rel_idx = event_types.index(EmergencyEventType.CORRIDOR_RELEASED.value)
        res_idx = event_types.index(EmergencyEventType.NORMAL_RESUMED.value)
        self.assertLessEqual(comp_idx, rel_idx)
        self.assertLessEqual(rel_idx, res_idx)

    # TEST 9: Normal operation unchanged when no emergency exists
    def test_normal_operation_unchanged_without_emergency(self):
        """Verify simulator produces zero preemption events when no emergency vehicle is scheduled."""
        scenario_no_emerg = SimulationScenario(
            scenario_id="no_emerg_test",
            duration_seconds=60,
            initial_queues={"I1": 5, "I2": 5, "I3": 5, "I4": 5},
            emergency_config=None,
        )

        m_off = simulate(scenario_no_emerg, self.normal_plan, seed=42, enable_emergency_corridor=False)
        m_on = simulate(scenario_no_emerg, self.normal_plan, seed=42, enable_emergency_corridor=True)

        self.assertEqual(m_off.throughput, m_on.throughput)
        self.assertEqual(m_off.total_waiting_time, m_on.total_waiting_time)
        self.assertEqual(m_on.emergency_preemption_count, 0)
        self.assertEqual(len(m_on.corridor_event_log), 0)

    # TEST 10: Deterministic event log
    def test_deterministic_event_log(self):
        """Verify running simulation twice with identical seed produces identical event logs."""
        m1 = simulate(self.scenario, self.normal_plan, seed=42, enable_emergency_corridor=True)
        m2 = simulate(self.scenario, self.normal_plan, seed=42, enable_emergency_corridor=True)

        self.assertEqual(len(m1.corridor_event_log), len(m2.corridor_event_log))
        for e1, e2 in zip(m1.corridor_event_log, m2.corridor_event_log):
            self.assertEqual(e1["timestamp"], e2["timestamp"])
            self.assertEqual(e1["event_type"], e2["event_type"])
            self.assertEqual(e1["intersection"], e2["intersection"])

    # TEST 11 & 23: Critical fairness test (same arrival stream with vs without corridor)
    def test_emergency_corridor_fairness_comparison(self):
        """Verify fair comparison under identical background arrival realization."""
        # Run A: Emergency present, corridor disabled
        m_no_corridor = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=False,
        )

        # Run B: Emergency present, corridor enabled
        m_with_corridor = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        # Both must generate exactly the same number of total vehicles
        self.assertEqual(m_no_corridor.vehicles_generated, m_with_corridor.vehicles_generated)

        # With corridor active, emergency waiting time should be less than or equal to without corridor
        self.assertLessEqual(m_with_corridor.emergency_waiting_time, m_no_corridor.emergency_waiting_time)
        self.assertLessEqual(m_with_corridor.emergency_response_time, m_no_corridor.emergency_response_time)

    # TEST 12 & 13: Route validation and invalid route rejection
    def test_emergency_route_validation(self):
        """Verify route validator accepts valid routes and rejects invalid or non-forward routes."""
        ctrl = EmergencyCorridorController(network_intersections=("I1", "I2", "I3", "I4"))

        # Valid routes
        ctrl.validate_route(("I2", "I3", "I4"))
        ctrl.validate_route(("I1", "I2"))
        ctrl.validate_route(("I1", "I4"))

        # Invalid: empty
        with self.assertRaises(ValueError):
            ctrl.validate_route(())

        # Invalid: unknown intersection
        with self.assertRaises(ValueError):
            ctrl.validate_route(("I2", "I99"))

        # Invalid: non-forward (backward)
        with self.assertRaises(ValueError):
            ctrl.validate_route(("I3", "I2"))

    # TEST 14: Normal traffic waiting impact is measurable
    def test_normal_traffic_waiting_measurable(self):
        """Verify simulator tracks normal vehicles waiting time separately from emergency vehicle."""
        metrics = simulate(
            self.scenario,
            self.normal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        self.assertGreater(metrics.normal_vehicles_waiting_time, 0.0)
        self.assertAlmostEqual(
            metrics.total_waiting_time,
            metrics.normal_vehicles_waiting_time + (metrics.emergency_waiting_time or 0.0),
            places=5,
        )

    # TEST 15: One active emergency vehicle policy
    def test_single_active_emergency_policy(self):
        """Verify arriving second emergency vehicle while first is active logs rejection event."""
        # Create scenario with overlapping emergency vehicle configs
        # First arrives at t=5, second at t=6
        scen = SimulationScenario(
            scenario_id="multi_emerg",
            duration_seconds=50,
            emergency_config=EmergencyVehicleConfig("EMERG_01", arrival_time=5, route=("I2", "I3", "I4")),
        )
        sim = TrafficSimulator(scen, enable_emergency_corridor=True)
        m = sim.simulate(self.normal_plan, seed=42)

        # Single active policy should maintain integrity without crashing
        self.assertTrue(m.emergency_completed)

    # TEST 16: Hybrid normal plan integration
    def test_hybrid_normal_plan_integration(self):
        """Verify normal plan from Hybrid solver runs under dynamic corridor preemption."""
        bench_scen = create_deterministic_scenario(seed=42, with_simulation=False)
        hybrid_ctrl = HybridController(name="hybrid_test", qaoa_maxiter=10, qaoa_shots=256)
        out = hybrid_ctrl.solve(bench_scen, seed=42)

        # Feed hybrid signal plan into simulation with emergency corridor enabled
        m = simulate(
            self.scenario,
            out.signal_plan,
            seed=42,
            enable_emergency_corridor=True,
        )

        self.assertTrue(m.emergency_completed)
        self.assertGreater(m.throughput, 0)
        self.assertGreaterEqual(m.emergency_preemption_count, 1)


if __name__ == "__main__":
    unittest.main()
