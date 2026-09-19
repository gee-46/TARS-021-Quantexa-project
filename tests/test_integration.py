"""Unit tests for Phase 16: QuantumFlow End-to-End Integration Contract & Demo Hardening."""

import unittest
import json
import numpy as np

from simulation.integration import (
    QuantumFlowRunResult,
    RunComparisonResult,
    run_quantumflow_demo,
    compare_runs,
    create_canonical_demo_scenario,
    _to_json_safe,
)
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from simulation.engine import simulate
from optimization.controllers import (
    HybridController,
    SimulatedAnnealingController,
    FixedTimeController,
    RuleBasedController,
)


class TestIntegrationContract(unittest.TestCase):
    """Comprehensive test suite for Phase 16 integration contracts, execution, and serialization."""

    def setUp(self):
        self.scenario = create_canonical_demo_scenario(seed=42)
        self.seed = 42

    # TEST 1: End-to-end hybrid run succeeds
    def test_end_to_end_hybrid_run_succeeds(self):
        """Verify run_quantumflow_demo runs the full pipeline with HybridController and returns valid result."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="hybrid",
            qaoa_p=1,
            qaoa_maxiter=10,
            qaoa_shots=256,
        )
        self.assertIsInstance(res, QuantumFlowRunResult)
        self.assertEqual(res.optimization_status, "success")
        self.assertGreater(res.throughput, 0)
        self.assertEqual(res.simulation_duration, 300)

    # TEST 2: Result contains a valid normal signal plan
    def test_result_contains_valid_normal_signal_plan(self):
        """Verify normal_signal_plan contains valid durations for all intersections."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        self.assertIsInstance(res.normal_signal_plan, dict)
        self.assertEqual(set(res.normal_signal_plan.keys()), {"I1", "I2", "I3", "I4"})
        for inter, dur in res.normal_signal_plan.items():
            self.assertIn(dur, {15, 30, 45})

    # TEST 3: Result is JSON serializable
    def test_result_is_json_serializable(self):
        """Verify json.dumps(res.to_dict()) executes without error and matches round-trip json.loads."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="sa",
            sa_num_reads=20,
            sa_num_sweeps=100,
        )
        d = res.to_dict()
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)
        loaded = json.loads(json_str)
        self.assertEqual(loaded["scenario_id"], res.scenario_id)
        self.assertEqual(loaded["throughput"], res.throughput)

    # TEST 4: to_dict() contains only JSON-safe primitives recursively
    def test_to_dict_contains_only_json_safe_primitives(self):
        """Verify to_dict() contains no NumPy, custom object, or Enum types."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        d = res.to_dict()

        def assert_json_safe(val, path="root"):
            if val is None:
                return
            if isinstance(val, (str, int, float, bool)):
                # Ensure not raw numpy types
                self.assertNotIsInstance(val, np.number, f"NumPy number found at {path}: {val}")
                self.assertNotIsInstance(val, np.bool_, f"NumPy bool found at {path}: {val}")
                return
            if isinstance(val, list):
                for idx, item in enumerate(val):
                    assert_json_safe(item, f"{path}[{idx}]")
                return
            if isinstance(val, dict):
                for k, v in val.items():
                    self.assertIsInstance(k, str, f"Dict key at {path} is not str: {k}")
                    assert_json_safe(v, f"{path}.{k}")
                return
            self.fail(f"Non-JSON-safe object found at {path}: {type(val)} = {val}")

        assert_json_safe(d)

    # TEST 5: Hybrid optimization metadata is preserved
    def test_hybrid_optimization_metadata_preserved(self):
        """Verify solver, status, energy, runtime, fallback telemetry are present."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="hybrid",
            qaoa_p=1,
            qaoa_maxiter=10,
            qaoa_shots=256,
        )
        self.assertIn(res.optimization_solver, ("qaoa", "sa"))
        self.assertIsInstance(res.optimization_energy, float)
        self.assertGreaterEqual(res.optimization_runtime, 0.0)
        self.assertIsInstance(res.optimization_fallback_used, bool)
        self.assertTrue(res.onehot_valid)

    # TEST 6: Emergency-enabled run contains emergency telemetry
    def test_emergency_enabled_run_contains_emergency_metrics(self):
        """Verify dynamic green corridor reports detection, activation, clearance, and response time."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        self.assertTrue(res.emergency_present)
        self.assertTrue(res.emergency_corridor_enabled)
        self.assertEqual(res.emergency_detected_time, 20)
        self.assertEqual(res.emergency_corridor_activated_time, 20)
        self.assertTrue(res.emergency_completed)
        self.assertIsNotNone(res.emergency_completed_time)
        self.assertIsNotNone(res.emergency_response_time)
        self.assertIsNotNone(res.emergency_waiting_time)
        self.assertEqual(res.emergency_intersections_cleared, 3)
        self.assertGreaterEqual(res.emergency_preemption_count, 1)
        self.assertGreater(len(res.corridor_event_log), 0)

    # TEST 7: Emergency-disabled run does not falsely report emergency completion
    def test_emergency_disabled_run_does_not_falsely_report_completion(self):
        """Verify corridor activation and corridor completion times are None when corridor is disabled."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=False,
            controller="fixed",
        )
        self.assertTrue(res.emergency_present)
        self.assertFalse(res.emergency_corridor_enabled)
        self.assertIsNone(res.emergency_detected_time)
        self.assertIsNone(res.emergency_corridor_activated_time)
        self.assertIsNone(res.emergency_completed_time)
        self.assertEqual(res.emergency_preemption_count, 0)
        self.assertEqual(len(res.corridor_event_log), 0)

    # TEST 8: Same scenario + same seed produces deterministic metrics
    def test_same_seed_and_scenario_produces_deterministic_metrics(self):
        """Verify reproducibility across identical scenario and seed runs."""
        res1 = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        res2 = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        self.assertEqual(res1.throughput, res2.throughput)
        self.assertEqual(res1.average_waiting_time, res2.average_waiting_time)
        self.assertEqual(res1.max_queue, res2.max_queue)
        self.assertEqual(res1.emergency_response_time, res2.emergency_response_time)
        self.assertEqual(res1.optimization_energy, res2.optimization_energy)

    # TEST 9: Baseline and emergency-enabled runs use identical scenario and seed
    def test_baseline_and_emergency_runs_use_identical_seed_and_scenario(self):
        """Verify baseline (disabled) and corridor (enabled) runs share scenario ID and random seed."""
        res_baseline = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=False,
            controller="rule",
        )
        res_corridor = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="rule",
        )
        self.assertEqual(res_baseline.scenario_id, res_corridor.scenario_id)
        self.assertEqual(res_baseline.seed, res_corridor.seed)
        self.assertEqual(res_baseline.simulation_duration, res_corridor.simulation_duration)
        self.assertEqual(res_baseline.normal_signal_plan, res_corridor.normal_signal_plan)

    # TEST 10: compare_runs() calculates exact arithmetic deltas
    def test_compare_runs_calculates_exact_deltas(self):
        """Verify compare_runs computes strictly factual quantumflow - baseline arithmetic deltas."""
        base = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=False,
            controller="fixed",
        )
        active = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        deltas = compare_runs(baseline=base, quantumflow=active)

        self.assertIsInstance(deltas, RunComparisonResult)
        self.assertEqual(deltas.throughput_delta, active.throughput - base.throughput)
        self.assertEqual(deltas.max_queue_delta, active.max_queue - base.max_queue)
        self.assertAlmostEqual(
            deltas.normal_wait_delta,
            active.normal_vehicles_waiting_time - base.normal_vehicles_waiting_time,
            places=5,
        )
        self.assertAlmostEqual(
            deltas.average_wait_delta,
            active.average_waiting_time - base.average_waiting_time,
            places=5,
        )
        self.assertEqual(
            deltas.preemption_delta,
            active.emergency_preemption_count - base.emergency_preemption_count,
        )
        self.assertAlmostEqual(
            deltas.energy_delta,
            active.optimization_energy - base.optimization_energy,
            places=5,
        )

        # Dictionary-like indexing support
        self.assertEqual(deltas["throughput_delta"], deltas.throughput_delta)
        self.assertEqual(deltas.get("throughput_delta"), deltas.throughput_delta)

    # TEST 11: Controller selection works for hybrid, sa, fixed, rule
    def test_controller_selection_supports_all_controllers(self):
        """Verify all supported controller identifiers instantiate and run successfully."""
        controllers = ["hybrid", "sa", "fixed", "rule"]
        for ctrl_name in controllers:
            res = run_quantumflow_demo(
                scenario=self.scenario,
                seed=self.seed,
                enable_emergency_corridor=True,
                controller=ctrl_name,
                qaoa_p=1,
                qaoa_maxiter=5,
                qaoa_shots=128,
                sa_num_reads=10,
                sa_num_sweeps=50,
            )
            self.assertIsInstance(res, QuantumFlowRunResult)
            self.assertEqual(res.optimization_status, "success")
            self.assertGreater(res.throughput, 0)

    # TEST 12: Invalid controller name raises a clear ValueError
    def test_invalid_controller_name_raises_clear_error(self):
        """Verify passing an unrecognized controller identifier raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            run_quantumflow_demo(
                scenario=self.scenario,
                seed=self.seed,
                controller="unsupported_quantum_magic",
            )
        self.assertIn("Unknown or unsupported controller", str(ctx.exception))

    # TEST 13: Emergency route is not mutated
    def test_emergency_route_not_mutated(self):
        """Verify emergency vehicle route specification remains immutable throughout run."""
        orig_route = tuple(self.scenario.emergency_config.route)
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        self.assertEqual(self.scenario.emergency_config.route, orig_route)

    # TEST 14: Normal signal plan in result is optimizer output before emergency overrides
    def test_normal_signal_plan_is_optimizer_output_before_emergency(self):
        """Verify normal_signal_plan represents static offline plan regardless of dynamic emergency overrides."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
            default_duration=30,
        )
        # Fixed controller was set to 30s everywhere
        for dur in res.normal_signal_plan.values():
            self.assertEqual(dur, 30)

    # TEST 15: Event log survives serialization
    def test_event_log_survives_serialization(self):
        """Verify corridor event log survives to_dict() and JSON round-trip without data loss."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        d = res.to_dict()
        self.assertIn("corridor_event_log", d)
        self.assertIsInstance(d["corridor_event_log"], list)
        self.assertGreater(len(d["corridor_event_log"]), 0)

        json_bytes = json.dumps(d)
        reloaded = json.loads(json_bytes)
        self.assertEqual(len(reloaded["corridor_event_log"]), len(res.corridor_event_log))
        self.assertEqual(
            reloaded["corridor_event_log"][0]["event_type"],
            res.corridor_event_log[0]["event_type"],
        )

    # TEST 16: Recovery state is represented correctly
    def test_recovery_state_represented_correctly(self):
        """Verify recovery_completed is True when emergency completes and corridor releases."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        self.assertTrue(res.emergency_completed)
        self.assertTrue(res.recovery_completed)
        self.assertEqual(res.final_signal_states["I2"], "NORMAL")
        self.assertEqual(res.final_signal_states["I3"], "NORMAL")
        self.assertEqual(res.final_signal_states["I4"], "NORMAL")

    # TEST 17: JSON serialization handles Enum/dataclass/NumPy values if they occur
    def test_json_safe_converter_handles_diverse_types(self):
        """Verify _to_json_safe properly serializes nested combinations of types."""
        nested = {
            "np_int": np.int64(42),
            "np_float": np.float64(3.1415),
            "np_bool": np.bool_(True),
            "np_arr": np.array([1, 2, 3]),
            "tuple_val": (10, 20),
            "none_val": None,
        }
        sanitized = _to_json_safe(nested)
        self.assertIsInstance(sanitized["np_int"], int)
        self.assertIsInstance(sanitized["np_float"], float)
        self.assertIsInstance(sanitized["np_bool"], bool)
        self.assertIsInstance(sanitized["np_arr"], list)
        self.assertIsInstance(sanitized["tuple_val"], list)
        self.assertIsNone(sanitized["none_val"])
        # JSON dump must succeed
        json.dumps(sanitized)

    # TEST 18: compare_runs() correctly returns None for unavailable emergency metrics
    def test_compare_runs_handles_unavailable_emergency_metrics(self):
        """Verify compare_runs returns None for emergency deltas if either run has no emergency data."""
        no_emerg_scen = SimulationScenario(
            scenario_id="no_emerg_scen",
            duration_seconds=100,
            emergency_config=None,
        )
        res1 = run_quantumflow_demo(scenario=no_emerg_scen, seed=42, controller="fixed")
        res2 = run_quantumflow_demo(scenario=no_emerg_scen, seed=42, controller="fixed")
        deltas = compare_runs(baseline=res1, quantumflow=res2)

        self.assertIsNone(deltas.emergency_response_delta)
        self.assertIsNone(deltas.emergency_wait_delta)
        self.assertEqual(deltas.throughput_delta, 0)

    # TEST 19: to_dict() does not contain raw NumPy objects
    def test_to_dict_no_raw_numpy_objects(self):
        """Verify result.to_dict() contains zero instances of np.generic or np.ndarray."""
        res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
        )
        d = res.to_dict()
        for k, v in d.items():
            self.assertNotIsInstance(v, np.generic, f"Field '{k}' contains raw NumPy generic: {type(v)}")
            self.assertNotIsInstance(v, np.ndarray, f"Field '{k}' contains raw NumPy ndarray: {type(v)}")

    # TEST 20: Existing simulator metrics remain unchanged by integration wrapper
    def test_existing_simulator_metrics_unchanged_by_integration_wrapper(self):
        """Verify run_quantumflow_demo metrics match direct simulator.simulate outputs exactly."""
        normal_plan = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
        direct_metrics = simulate(
            scenario=self.scenario,
            signal_plan=normal_plan,
            seed=self.seed,
            enable_emergency_corridor=True,
        )
        wrapped_res = run_quantumflow_demo(
            scenario=self.scenario,
            seed=self.seed,
            enable_emergency_corridor=True,
            controller="fixed",
            default_duration=30,
        )
        self.assertEqual(wrapped_res.throughput, direct_metrics.throughput)
        self.assertEqual(wrapped_res.total_waiting_time if hasattr(wrapped_res, "total_waiting_time") else wrapped_res.average_waiting_time, direct_metrics.average_waiting_time)
        self.assertEqual(wrapped_res.max_queue, direct_metrics.max_queue)
        self.assertEqual(wrapped_res.emergency_response_time, direct_metrics.emergency_response_time)


if __name__ == "__main__":
    unittest.main()
