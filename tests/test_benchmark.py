"""Unit tests for Phase 13: Controlled Optimization Benchmark and Evaluation Framework."""

import unittest
import os
import json
import tempfile
import numpy as np

from optimization.variables import NUM_VARIABLES, INTERSECTIONS
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.controllers import (
    BaseController,
    ControllerOutput,
    HybridController,
    SimulatedAnnealingController,
    FixedTimeController,
    RuleBasedController,
    signal_plan_to_binary_vector,
)
from optimization.benchmark_metrics import (
    OptimizationMetrics,
    TrafficMetrics,
    TrialResult,
    MetricSummary,
    calculate_metric_summary,
    summarize_results,
)
from optimization.benchmark import (
    BenchmarkScenario,
    create_deterministic_scenario,
    create_random_scenario,
    run_benchmark,
    save_results_json,
    load_results_json,
    format_comparison_table,
)


class TestBenchmarkFramework(unittest.TestCase):
    """Test suite covering scenario generation, controller execution, metrics, and serialization."""

    def setUp(self):
        self.scenario = create_deterministic_scenario(scenario_id="test_phase7_scen", seed=42)

    # TEST 1 & 2: Scenario creation determinism
    def test_scenario_creation_determinism(self):
        """Verify scenario construction is deterministic and identical for same seed."""
        scen1 = create_deterministic_scenario(seed=42)
        scen2 = create_deterministic_scenario(seed=42)

        self.assertEqual(scen1.scenario_id, scen2.scenario_id)
        self.assertEqual(scen1.traffic_state, scen2.traffic_state)
        self.assertEqual(scen1.edges, scen2.edges)
        np.testing.assert_allclose(scen1.qubo_model.Q, scen2.qubo_model.Q)
        self.assertAlmostEqual(scen1.qubo_model.offset, scen2.qubo_model.offset)

        # Randomized scenario with same seed
        rand1 = create_random_scenario("rand_scen", seed=99)
        rand2 = create_random_scenario("rand_scen", seed=99)
        np.testing.assert_allclose(rand1.qubo_model.Q, rand2.qubo_model.Q)

    # TEST 3: Fixed-time controller
    def test_fixed_time_controller(self):
        """Verify fixed-time controller returns expected configurable signal timing plan."""
        ctrl_default = FixedTimeController(name="fixed_30", default_duration=30)
        out_def = ctrl_default.solve(self.scenario)

        self.assertEqual(out_def.signal_plan, {"I1": 30, "I2": 30, "I3": 30, "I4": 30})
        self.assertTrue(out_def.onehot_valid)
        self.assertEqual(out_def.solver_used, "fixed")

        # Custom plan
        custom_plan = {"I1": 15, "I2": 45, "I3": 45, "I4": 45}
        ctrl_custom = FixedTimeController(name="fixed_custom", custom_plan=custom_plan)
        out_cust = ctrl_custom.solve(self.scenario)
        self.assertEqual(out_cust.signal_plan, custom_plan)
        self.assertTrue(out_cust.onehot_valid)
        self.assertTrue(out_cust.emergency_valid)

    # TEST 4: Rule-based controller determinism
    def test_rule_based_controller_determinism(self):
        """Verify rule-based heuristic controller decisions are deterministic and follow thresholds."""
        # For Phase 7: I1(q=20, d=0.5)->30s, I2(q=35, d=0.9)->45s, I3(q=15, d=0.6)->30s, I4(q=30, d=0.8)->45s
        ctrl = RuleBasedController(name="rule_based")
        out1 = ctrl.solve(self.scenario)
        out2 = ctrl.solve(self.scenario)

        expected_plan = {"I1": 30, "I2": 45, "I3": 30, "I4": 45}
        self.assertEqual(out1.signal_plan, expected_plan)
        self.assertEqual(out2.signal_plan, expected_plan)
        self.assertTrue(out1.onehot_valid)
        self.assertEqual(out1.solver_used, "rule_based")

        # With emergency override (I2, I3, I4 forced to 45s)
        ctrl_emerg = RuleBasedController(name="rule_emerg", respect_emergency=True)
        out_emerg = ctrl_emerg.solve(self.scenario)
        self.assertEqual(out_emerg.signal_plan, {"I1": 30, "I2": 45, "I3": 45, "I4": 45})
        self.assertTrue(out_emerg.emergency_valid)

    # TEST 5: Hybrid controller adapter
    def test_hybrid_controller_adapter(self):
        """Verify hybrid controller executes and returns valid signal plan on deterministic scenario."""
        ctrl = HybridController(name="hybrid_test", qaoa_maxiter=10, qaoa_shots=256, sa_num_reads=20, sa_num_sweeps=50)
        out = ctrl.solve(self.scenario, seed=42)

        self.assertEqual(out.controller_name, "hybrid_test")
        self.assertTrue(out.onehot_valid)
        self.assertTrue(out.emergency_valid)
        self.assertIn(out.solver_used, ["qaoa", "sa"])
        expected_e = float(self.scenario.qubo_model.energy(out.binary_vector, include_offset=True))
        self.assertAlmostEqual(out.qubo_energy, expected_e, places=8)

    # TEST 6: Simulated Annealing controller adapter
    def test_sa_controller_adapter(self):
        """Verify SA controller adapter executes and returns valid signal plan."""
        ctrl = SimulatedAnnealingController(name="sa_test", num_reads=50, num_sweeps=100)
        out = ctrl.solve(self.scenario, seed=42)

        self.assertEqual(out.controller_name, "sa_test")
        self.assertTrue(out.onehot_valid)
        self.assertTrue(out.emergency_valid)
        self.assertEqual(out.solver_used, "sa")
        expected_e = float(self.scenario.qubo_model.energy(out.binary_vector, include_offset=True))
        self.assertAlmostEqual(out.qubo_energy, expected_e, places=8)

    # TEST 7: Generic controller interface uniformity
    def test_controller_interface_uniformity(self):
        """Verify all 4 controller types conform to BaseController interface."""
        controllers = [
            FixedTimeController(),
            RuleBasedController(),
            SimulatedAnnealingController(num_reads=10, num_sweeps=50),
            HybridController(qaoa_maxiter=5, qaoa_shots=100, sa_num_reads=10, sa_num_sweeps=50),
        ]

        for ctrl in controllers:
            self.assertIsInstance(ctrl, BaseController)
            out = ctrl.solve(self.scenario, seed=123)
            self.assertIsInstance(out, ControllerOutput)
            self.assertEqual(len(out.binary_vector), NUM_VARIABLES)
            self.assertEqual(len(out.canonical_bitstring), NUM_VARIABLES)
            self.assertTrue(all(k in out.signal_plan for k in INTERSECTIONS))
            self.assertTrue(np.isfinite(out.qubo_energy))

    # TEST 8 & 9: Benchmark execution, schema, and distinct trial seeds
    def test_run_benchmark_trials_and_seeds(self):
        """Verify run_benchmark executes multiple trials with distinct deterministic seeds."""
        controllers = [
            FixedTimeController(name="fixed_30"),
            RuleBasedController(name="rule_based"),
        ]

        num_trials = 3
        base_seed = 100
        results = run_benchmark([self.scenario], controllers, num_trials=num_trials, base_seed=base_seed)

        self.assertEqual(len(results), len(controllers) * num_trials)

        # Check distinct trial seeds per controller
        fixed_trials = [r for r in results if r.controller_name == "fixed_30"]
        seeds = [r.seed for r in fixed_trials]
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(seeds, [base_seed + t * 1000 + self.scenario.seed for t in range(num_trials)])

        # Verify schema
        for r in results:
            self.assertEqual(r.scenario_id, self.scenario.scenario_id)
            self.assertIn("status", r.optimization_metrics.to_dict())
            self.assertIn("qubo_energy", r.optimization_metrics.to_dict())
            self.assertIn("runtime_seconds", r.optimization_metrics.to_dict())
            self.assertTrue(r.traffic_metrics.available)
            self.assertGreater(r.traffic_metrics.throughput, 0)

    # TEST 10: Statistical summaries
    def test_statistical_summaries(self):
        """Verify descriptive statistics (mean, median, std, min, max) calculations."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        summary = calculate_metric_summary(values, "test_metric")

        self.assertEqual(summary.count, 5)
        self.assertAlmostEqual(summary.mean, 30.0)
        self.assertAlmostEqual(summary.median, 30.0)
        self.assertAlmostEqual(summary.min, 10.0)
        self.assertAlmostEqual(summary.max, 50.0)
        self.assertAlmostEqual(summary.std, np.std(values, ddof=1))

        # Test summarize_results on trial results
        controllers = [FixedTimeController(name="fixed_30")]
        results = run_benchmark([self.scenario], controllers, num_trials=3, base_seed=42)
        summary_dict = summarize_results(results)

        scen_summary = summary_dict[self.scenario.scenario_id]["fixed_30"]
        self.assertEqual(scen_summary["num_trials"], 3)
        self.assertIn("qubo_energy", scen_summary)
        self.assertIn("runtime_seconds", scen_summary)

    # TEST 11: Exact optimum validation does not alter output
    def test_exact_optimum_validation_preserves_output(self):
        """Verify exact ground truth comparison records gap without altering optimizer result."""
        ctrl = FixedTimeController(custom_plan={"I1": 45, "I2": 45, "I3": 45, "I4": 45})
        results = run_benchmark([self.scenario], [ctrl], num_trials=1, base_seed=42)

        r = results[0]
        self.assertAlmostEqual(r.optimization_metrics.qubo_energy, self.scenario.exact_optimum_energy)
        self.assertAlmostEqual(r.optimization_metrics.optimality_gap, 0.0)
        self.assertTrue(r.optimization_metrics.exact_optimum_found)

    # TEST 12: JSON serialization and deserialization
    def test_json_export_and_loading(self):
        """Verify benchmark trial results cleanly serialize to and deserialize from JSON."""
        controllers = [
            FixedTimeController(name="fixed_30"),
            RuleBasedController(name="rule_based"),
        ]
        results = run_benchmark([self.scenario], controllers, num_trials=2, base_seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "benchmark_results.json")
            save_results_json(results, file_path)

            self.assertTrue(os.path.exists(file_path))

            loaded_results = load_results_json(file_path)
            self.assertEqual(len(loaded_results), len(results))

            for orig, loaded in zip(results, loaded_results):
                self.assertEqual(orig.scenario_id, loaded.scenario_id)
                self.assertEqual(orig.trial_index, loaded.trial_index)
                self.assertEqual(orig.seed, loaded.seed)
                self.assertEqual(orig.controller_name, loaded.controller_name)
                self.assertEqual(orig.signal_plan, loaded.signal_plan)
                self.assertAlmostEqual(
                    orig.optimization_metrics.qubo_energy,
                    loaded.optimization_metrics.qubo_energy,
                )
                self.assertEqual(
                    orig.optimization_metrics.best_bitstring,
                    loaded.optimization_metrics.best_bitstring,
                )

    def test_format_comparison_table(self):
        """Verify textual comparison table formatting helper."""
        controllers = [FixedTimeController(name="fixed_30")]
        results = run_benchmark([self.scenario], controllers, num_trials=2, base_seed=42)
        table_str = format_comparison_table(results)

        self.assertIn("Scenario", table_str)
        self.assertIn("fixed_30", table_str)
        self.assertIn("QUBO Energy", table_str)


if __name__ == "__main__":
    unittest.main()
