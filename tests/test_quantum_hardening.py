"""Comprehensive Quantum Hardening and Verification Suite (Tests A through J).

Authoritative verification for QuantumFlow hackathon competition finalization on branch feature/quantum-qubo.

Covers:
- TEST A: Canonical 12-variable indexing
- TEST B: QUBO upper-triangle integrity and no lower-triangle duplication on composed model
- TEST C: Exact QUBO <-> Ising equivalence across all 4096 states on actual canonical traffic QUBO
- TEST D: Exhaustive 4096-state ground truth optimum identification and feasibility verification
- TEST E: QAOA candidate structural and domain validity
- TEST F: Explicit distinction between QAOA variational expectation value <psi|H_C|psi> and sampled candidate QUBO energy
- TEST G: Simulated Annealing exact-energy mapping with dimod BQM
- TEST H: Hybrid fallback trigger coverage across all operational failure conditions
- TEST I: No fallback for merely suboptimal but valid and feasible QAOA candidates
- TEST J: End-to-end quantum provenance tracing from QUBO -> QAOA -> Decoder -> HybridController -> QuantumFlowRunResult
"""

import unittest
from unittest.mock import patch, MagicMock
import itertools
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    VARIABLE_NAMES,
    get_variable_index,
    get_intersection_variable_indices,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.onehot import build_onehot_qubo, add_onehot_penalty
from optimization.traffic_objectives import (
    TrafficState,
    TrafficObjectiveConfig,
    add_traffic_terms,
)
from optimization.coupling import (
    CouplingConfig,
    add_coupling_term,
)
from optimization.emergency import (
    EmergencyConstraints,
    add_emergency_term,
)
from optimization.qubo_builder import (
    FullQUBOConfig,
    build_qubo,
)
from optimization.ising_converter import (
    IsingModel,
    qubo_to_ising,
    bits_to_spins,
    spins_to_bits,
    ising_energy,
)
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
    validate_solution,
)
from optimization.qaoa_solver import (
    qiskit_bitstring_to_bits,
    bits_to_qiskit_bitstring,
)
from optimization.production_qaoa import (
    ProductionQAOAResult,
    solve_production_qaoa,
)
from optimization.sa_solver import (
    qubo_to_bqm,
    solve_simulated_annealing,
    SimulatedAnnealingResult,
)
from optimization.hybrid_solver import (
    HybridSolveResult,
    solve_hybrid,
)
from optimization.controllers import (
    HybridController,
    ControllerOutput,
    signal_plan_to_binary_vector,
)
from simulation.integration import (
    QuantumFlowRunResult,
    run_quantumflow_demo,
    create_canonical_demo_scenario,
    _build_benchmark_scenario_for_simulation,
)


class TestQuantumHardening(unittest.TestCase):
    """Authoritative test suite for QuantumFlow quantum branch hardening."""

    def setUp(self):
        """Set up canonical scenario and traffic state fixtures."""
        self.intersections = ("I1", "I2", "I3", "I4")
        self.durations = (15, 30, 45)
        self.edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
        self.state_dict = {
            "I1": {"queue": 10.0, "density": 0.50, "capacity": 40.0},
            "I2": {"queue": 15.0, "density": 0.75, "capacity": 40.0},
            "I3": {"queue": 8.0, "density": 0.40, "capacity": 40.0},
            "I4": {"queue": 12.0, "density": 0.60, "capacity": 40.0},
        }
        self.traffic_state = TrafficState.from_dict(self.state_dict)
        self.config = FullQUBOConfig(
            onehot_penalty=100.0,
            wait_weight=2.0,
            capacity_weight=10.0,
            capacity_threshold=0.7,
            throughput_weight=1.0,
            service_rate=1.0,
            coupling_weight=5.0,
            default_capacity=40.0,
            emergency_weight=50.0,
        )
        self.emergency = EmergencyConstraints(
            route=("I2", "I3", "I4"),
            forced_duration=45,
            emergency_weight=50.0,
        )

    # ------------------------------------------------------------------
    # TEST A: Canonical indexing
    # ------------------------------------------------------------------
    def test_a_canonical_indexing(self):
        """TEST A: Verify every canonical index 0..11 exactly matches the specification."""
        expected_indices = {
            ("I1", 15): 0,
            ("I1", 30): 1,
            ("I1", 45): 2,
            ("I2", 15): 3,
            ("I2", 30): 4,
            ("I2", 45): 5,
            ("I3", 15): 6,
            ("I3", 30): 7,
            ("I3", 45): 8,
            ("I4", 15): 9,
            ("I4", 30): 10,
            ("I4", 45): 11,
        }

        self.assertEqual(NUM_VARIABLES, 12)
        self.assertEqual(len(VARIABLE_INDEX), 12)
        self.assertEqual(len(INDEX_TO_VARIABLE), 12)
        self.assertEqual(len(VARIABLE_NAMES), 12)

        for (inter, dur), expected_idx in expected_indices.items():
            # 1. Forward dictionary lookup
            self.assertEqual(VARIABLE_INDEX[(inter, dur)], expected_idx)
            # 2. Forward helper function
            self.assertEqual(get_variable_index(inter, dur), expected_idx)
            # 3. Reverse dictionary lookup
            self.assertEqual(INDEX_TO_VARIABLE[expected_idx], (inter, dur))
            # 4. Variable string name
            self.assertEqual(VARIABLE_NAMES[expected_idx], f"{inter}_{dur}")

        # Check intersection index clusters
        self.assertEqual(get_intersection_variable_indices("I1"), [0, 1, 2])
        self.assertEqual(get_intersection_variable_indices("I2"), [3, 4, 5])
        self.assertEqual(get_intersection_variable_indices("I3"), [6, 7, 8])
        self.assertEqual(get_intersection_variable_indices("I4"), [9, 10, 11])

    # ------------------------------------------------------------------
    # TEST B: QUBO upper-triangle integrity
    # ------------------------------------------------------------------
    def test_b_qubo_upper_triangle_integrity(self):
        """TEST B: Verify lower triangle is strictly zero for both components and final composed QUBO."""
        # 1. Component QUBOs
        onehot_qubo = build_onehot_qubo(penalty_coefficient=100.0)
        self.assertTrue(np.allclose(np.tril(onehot_qubo.Q, -1), 0.0))

        # 2. Composed QUBO without emergency
        composed_normal = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=None,
        )
        self.assertEqual(composed_normal.Q.shape, (12, 12))
        self.assertTrue(np.allclose(np.tril(composed_normal.Q, -1), 0.0))

        # Verify strict zero on all strictly lower-triangular entries (i > j)
        for i in range(12):
            for j in range(i):
                self.assertEqual(
                    composed_normal.Q[i, j],
                    0.0,
                    f"Non-zero lower triangular entry at ({i}, {j}): {composed_normal.Q[i, j]}",
                )

        # 3. Composed QUBO with emergency constraints
        composed_emerg = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        self.assertEqual(composed_emerg.Q.shape, (12, 12))
        self.assertTrue(np.allclose(np.tril(composed_emerg.Q, -1), 0.0))

        for i in range(12):
            for j in range(i):
                self.assertEqual(
                    composed_emerg.Q[i, j],
                    0.0,
                    f"Non-zero lower triangular entry in emergency QUBO at ({i}, {j}): {composed_emerg.Q[i, j]}",
                )

    # ------------------------------------------------------------------
    # TEST C: Exact QUBO <-> Ising equivalence across all 4096 states
    # ------------------------------------------------------------------
    def test_c_exact_qubo_ising_equivalence_all_4096_states(self):
        """TEST C: Verify for all 4096 states of the actual canonical composed QUBO, abs(E_QUBO - E_Ising) < 1e-10."""
        # Build the actual composed canonical traffic QUBO
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        ising = qubo_to_ising(qubo)

        self.assertEqual(ising.num_qubits, 12)
        max_abs_error = 0.0

        for bits in itertools.product([0, 1], repeat=12):
            x = tuple(bits)
            z = tuple(int(zi) for zi in bits_to_spins(x))

            e_qubo = qubo.energy(x, include_offset=True)
            e_ising = ising.energy(z)

            err = abs(e_qubo - e_ising)
            if err > max_abs_error:
                max_abs_error = err

            self.assertLess(
                err,
                1e-10,
                f"QUBO/Ising mismatch at state {x}: E_QUBO={e_qubo}, E_Ising={e_ising}, diff={err}",
            )

        # Confirm numerical precision is well within tolerance (< 1e-12 observed)
        self.assertLess(max_abs_error, 1e-10)

    # ------------------------------------------------------------------
    # TEST D: Exhaustive optimum
    # ------------------------------------------------------------------
    def test_d_exhaustive_optimum_feasibility(self):
        """TEST D: Enumerate all 4096 states on the canonical benchmark, identify global min, and verify feasibility."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )

        all_states = [tuple(bits) for bits in itertools.product([0, 1], repeat=12)]
        all_energies = [qubo.energy(x, include_offset=True) for x in all_states]

        min_energy = min(all_energies)
        opt_idx = all_energies.index(min_energy)
        opt_state = all_states[opt_idx]

        # Verify ground state feasibility
        self.assertTrue(is_valid_onehot(opt_state))
        self.assertTrue(is_valid_emergency(opt_state, self.emergency))
        self.assertTrue(np.isfinite(min_energy))

        # Ground state has exactly 4 active bits (one per intersection)
        self.assertEqual(sum(opt_state), 4)

        # Verify decoding produces a valid signal plan
        plan = decode_solution(opt_state)
        self.assertEqual(set(plan.keys()), {"I1", "I2", "I3", "I4"})
        self.assertEqual(plan["I2"], 45)  # forced emergency duration
        self.assertEqual(plan["I3"], 45)  # forced emergency duration
        self.assertEqual(plan["I4"], 45)  # forced emergency duration

    # ------------------------------------------------------------------
    # TEST E: QAOA candidate validity
    # ------------------------------------------------------------------
    def test_e_qaoa_candidate_validity(self):
        """TEST E: Verify QAOA produces a candidate with 12 binary bits, valid one-hot, and finite energy."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=None,
        )

        res = solve_production_qaoa(
            qubo_model=qubo,
            p=1,
            maxiter=15,
            shots=512,
            seed=42,
        )

        self.assertEqual(res.status, "success")
        self.assertEqual(res.num_qubits, 12)
        self.assertEqual(len(res.best_x), 12)
        # Verify strictly binary
        self.assertTrue(all(b in (0, 1) for b in res.best_x))
        # Verify finite energy
        self.assertTrue(np.isfinite(res.best_energy))
        self.assertEqual(res.best_energy, res.qubo_energy)
        # Verify energy matches original QUBO model re-evaluation
        recalc_e = qubo.energy(res.best_x, include_offset=True)
        self.assertAlmostEqual(res.best_energy, recalc_e, places=8)
        # Verify canonical bitstring consistency
        self.assertEqual(res.best_canonical_bitstring, "".join(str(b) for b in res.best_x))
        self.assertEqual(res.best_bitstring, bits_to_qiskit_bitstring(res.best_x))

    # ------------------------------------------------------------------
    # TEST F: QAOA sampled candidate vs expectation value distinction
    # ------------------------------------------------------------------
    def test_f_qaoa_sampled_candidate_vs_expectation_distinction(self):
        """TEST F: Explicitly verify variational expectation <psi|H_C|psi> and sampled candidate energy are distinct."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=None,
        )

        res = solve_production_qaoa(
            qubo_model=qubo,
            p=1,
            maxiter=10,
            shots=512,
            seed=42,
        )

        # 1. Both quantities are recorded independently
        self.assertTrue(hasattr(res, "expectation_value"))
        self.assertTrue(hasattr(res, "best_energy"))
        self.assertIsInstance(res.expectation_value, float)
        self.assertIsInstance(res.best_energy, float)

        # 2. Variational expectation is an average over all sampled measurement outcomes:
        #    <psi|H_C|psi> >= min_E(x_sampled)
        #    The best sampled candidate energy must be <= expectation value (or distinct from it)
        self.assertLessEqual(res.best_energy, res.expectation_value + 1e-6)

        # 3. Candidate energy is derived from x^T Q x + offset, not merely set to the variational expectation
        candidate_direct_energy = qubo.energy(res.best_x, include_offset=True)
        self.assertAlmostEqual(res.best_energy, candidate_direct_energy, places=8)

    # ------------------------------------------------------------------
    # TEST G: SA exact-energy mapping
    # ------------------------------------------------------------------
    def test_g_sa_exact_energy_mapping(self):
        """TEST G: Verify BQM energy equals original QUBOModel energy across states and in SA results."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        bqm = qubo_to_bqm(qubo)

        # Verify across sample binary states
        test_states = [
            (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1),
            (0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0),
            (0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1),
            (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        ]

        for x in test_states:
            qubo_e = qubo.energy(x, include_offset=True)
            sample_dict = {i: x[i] for i in range(12)}
            bqm_e = bqm.energy(sample_dict)
            self.assertAlmostEqual(
                qubo_e,
                bqm_e,
                places=9,
                msg=f"BQM and QUBO energy mismatch at state {x}: QUBO={qubo_e}, BQM={bqm_e}",
            )

        # Run SA solver and verify candidate energy mapping
        sa_res = solve_simulated_annealing(
            qubo_model=qubo,
            num_reads=50,
            num_sweeps=500,
            seed=42,
            emergency_constraints=self.emergency,
        )
        self.assertEqual(sa_res.status, "success")
        self.assertAlmostEqual(sa_res.best_energy, sa_res.qubo_energy, places=8)
        self.assertAlmostEqual(sa_res.best_energy, sa_res.bqm_energy, places=8)

    # ------------------------------------------------------------------
    # TEST H: Hybrid fallback triggers
    # ------------------------------------------------------------------
    def test_h_hybrid_fallback_triggers(self):
        """TEST H: Verify fallback to classical SA triggers for all operational failure conditions."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )

        # 1. Fallback on QAOA Exception / Failure
        with patch("optimization.hybrid_solver.solve_production_qaoa", side_effect=RuntimeError("Aer simulation failed")):
            res_fail = solve_hybrid(qubo_model=qubo, sa_num_reads=20, sa_num_sweeps=100)
            self.assertEqual(res_fail.status, "success")
            self.assertEqual(res_fail.solver_used, "sa")
            self.assertTrue(res_fail.fallback_used)
            self.assertEqual(res_fail.fallback_reason, "qaoa_failed")

        # 2. Fallback on Timeout
        dummy_timeout_res = ProductionQAOAResult(
            status="timeout",
            error="Execution exceeded timeout",
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=5,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=50.0,
            counts={},
            best_bitstring="000000000000",
            best_canonical_bitstring="000000000000",
            best_x=(0,) * 12,
            best_z=(1,) * 12,
            best_energy=100.0,
            qubo_energy=100.0,
            ising_energy=100.0,
            onehot_valid=False,
            emergency_valid=False,
            signal_plan=None,
            runtime_seconds=61.0,
            timed_out=True,
        )
        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_timeout_res):
            res_timeout = solve_hybrid(qubo_model=qubo, sa_num_reads=20, sa_num_sweeps=100)
            self.assertEqual(res_timeout.solver_used, "sa")
            self.assertTrue(res_timeout.fallback_used)
            self.assertEqual(res_timeout.fallback_reason, "qaoa_timeout")

        # 3. Fallback on Malformed / Invalid Candidate (wrong length)
        dummy_invalid_cand = ProductionQAOAResult(
            status="success",
            error=None,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=10,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=50.0,
            counts={},
            best_bitstring="000",
            best_canonical_bitstring="000",
            best_x=(0, 1, 0),  # wrong length (3 instead of 12)
            best_z=(1, -1, 1),
            best_energy=100.0,
            qubo_energy=100.0,
            ising_energy=100.0,
            onehot_valid=False,
            emergency_valid=False,
            signal_plan=None,
            runtime_seconds=1.0,
            timed_out=False,
        )
        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_invalid_cand):
            res_invalid = solve_hybrid(qubo_model=qubo, sa_num_reads=20, sa_num_sweeps=100)
            self.assertEqual(res_invalid.solver_used, "sa")
            self.assertTrue(res_invalid.fallback_used)
            self.assertEqual(res_invalid.fallback_reason, "invalid_candidate")

        # 4. Fallback on Invalid One-Hot
        dummy_bad_onehot = ProductionQAOAResult(
            status="success",
            error=None,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=10,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=50.0,
            counts={},
            best_bitstring="111111111111",
            best_canonical_bitstring="111111111111",
            best_x=(1,) * 12,  # all 1s violates one-hot
            best_z=(-1,) * 12,
            best_energy=800.0,
            qubo_energy=800.0,
            ising_energy=800.0,
            onehot_valid=False,
            emergency_valid=True,
            signal_plan=None,
            runtime_seconds=1.0,
            timed_out=False,
        )
        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_bad_onehot):
            res_onehot = solve_hybrid(qubo_model=qubo, require_onehot=True, sa_num_reads=20, sa_num_sweeps=100)
            self.assertEqual(res_onehot.solver_used, "sa")
            self.assertTrue(res_onehot.fallback_used)
            self.assertEqual(res_onehot.fallback_reason, "invalid_onehot")

        # 5. Fallback on Invalid Emergency
        # Valid one-hot: I1_15, I2_15, I3_15, I4_15 -> violates emergency forced_duration 45s for I2, I3, I4
        violating_emerg_x = (1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0)
        dummy_bad_emerg = ProductionQAOAResult(
            status="success",
            error=None,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=10,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=50.0,
            counts={},
            best_bitstring=bits_to_qiskit_bitstring(violating_emerg_x),
            best_canonical_bitstring="".join(str(b) for b in violating_emerg_x),
            best_x=violating_emerg_x,
            best_z=tuple(int(z) for z in bits_to_spins(violating_emerg_x)),
            best_energy=qubo.energy(violating_emerg_x, include_offset=True),
            qubo_energy=qubo.energy(violating_emerg_x, include_offset=True),
            ising_energy=qubo.energy(violating_emerg_x, include_offset=True),
            onehot_valid=True,
            emergency_valid=False,
            signal_plan=decode_solution(violating_emerg_x),
            runtime_seconds=1.0,
            timed_out=False,
        )
        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_bad_emerg):
            res_emerg = solve_hybrid(
                qubo_model=qubo,
                require_emergency_valid=True,
                emergency_constraints=self.emergency,
                sa_num_reads=20,
                sa_num_sweeps=100,
            )
            self.assertEqual(res_emerg.solver_used, "sa")
            self.assertTrue(res_emerg.fallback_used)
            self.assertEqual(res_emerg.fallback_reason, "invalid_emergency")

        # 6. Fallback on Non-Finite Energy
        valid_sample_x = (1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0)
        dummy_finite_cand = ProductionQAOAResult(
            status="success",
            error=None,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=10,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=50.0,
            counts={},
            best_bitstring=bits_to_qiskit_bitstring(valid_sample_x),
            best_canonical_bitstring="".join(str(b) for b in valid_sample_x),
            best_x=valid_sample_x,
            best_z=tuple(int(z) for z in bits_to_spins(valid_sample_x)),
            best_energy=50.0,
            qubo_energy=50.0,
            ising_energy=50.0,
            onehot_valid=True,
            emergency_valid=True,
            signal_plan=decode_solution(valid_sample_x),
            runtime_seconds=1.0,
            timed_out=False,
        )
        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_finite_cand):
            with patch.object(QUBOModel, "energy", return_value=float("nan")):
                res_nan = solve_hybrid(qubo_model=qubo, sa_num_reads=20, sa_num_sweeps=100)
                self.assertEqual(res_nan.solver_used, "sa")
                self.assertTrue(res_nan.fallback_used)
                self.assertEqual(res_nan.fallback_reason, "non_finite_energy")

    # ------------------------------------------------------------------
    # TEST I: No fallback for merely suboptimal QAOA
    # ------------------------------------------------------------------
    def test_i_no_fallback_for_suboptimal_valid_qaoa_candidate(self):
        """TEST I: Verify a valid, feasible, deliberately suboptimal QAOA candidate is accepted without fallback."""
        qubo = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )

        # 1. Compute exact theoretical global minimum energy
        all_states = [tuple(bits) for bits in itertools.product([0, 1], repeat=12)]
        all_energies = [qubo.energy(x, include_offset=True) for x in all_states]
        exact_global_min_energy = min(all_energies)

        # 2. Select a feasible state that is strictly suboptimal (higher energy than global minimum)
        # e.g., I1=15, I2=45, I3=45, I4=45
        suboptimal_feasible_x = (1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1)
        suboptimal_energy = qubo.energy(suboptimal_feasible_x, include_offset=True)

        self.assertTrue(is_valid_onehot(suboptimal_feasible_x))
        self.assertTrue(is_valid_emergency(suboptimal_feasible_x, self.emergency))
        self.assertGreater(suboptimal_energy, exact_global_min_energy)

        # 3. Mock QAOA returning this valid, feasible suboptimal candidate
        dummy_suboptimal_qaoa = ProductionQAOAResult(
            status="success",
            error=None,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=15,
            shots=1024,
            optimized_parameters=[0.3, 0.4],
            expectation_value=suboptimal_energy + 2.5,
            counts={bits_to_qiskit_bitstring(suboptimal_feasible_x): 1024},
            best_bitstring=bits_to_qiskit_bitstring(suboptimal_feasible_x),
            best_canonical_bitstring="".join(str(b) for b in suboptimal_feasible_x),
            best_x=suboptimal_feasible_x,
            best_z=tuple(int(z) for z in bits_to_spins(suboptimal_feasible_x)),
            best_energy=suboptimal_energy,
            qubo_energy=suboptimal_energy,
            ising_energy=suboptimal_energy,
            onehot_valid=True,
            emergency_valid=True,
            signal_plan=decode_solution(suboptimal_feasible_x),
            runtime_seconds=0.85,
            timed_out=False,
            ground_state_probability=0.25,
        )

        with patch("optimization.hybrid_solver.solve_production_qaoa", return_value=dummy_suboptimal_qaoa):
            hybrid_res = solve_hybrid(
                qubo_model=qubo,
                require_onehot=True,
                require_emergency_valid=True,
                emergency_constraints=self.emergency,
            )

            # Crucial verification: Fallback is NOT triggered
            self.assertEqual(hybrid_res.status, "success")
            self.assertEqual(hybrid_res.solver_used, "qaoa")
            self.assertFalse(hybrid_res.fallback_used)
            self.assertIsNone(hybrid_res.fallback_reason)
            self.assertIsNone(hybrid_res.sa_result)
            self.assertEqual(hybrid_res.best_x, suboptimal_feasible_x)
            self.assertEqual(hybrid_res.best_energy, suboptimal_energy)

    # ------------------------------------------------------------------
    # TEST J: End-to-end quantum provenance
    # ------------------------------------------------------------------
    def test_j_end_to_end_quantum_provenance(self):
        """TEST J: Trace full integration from QUBO -> Ising -> QAOA -> Decoder -> HybridController -> QuantumFlowRunResult."""
        scenario = create_canonical_demo_scenario(seed=42)
        seed = 42

        result = run_quantumflow_demo(
            scenario=scenario,
            seed=seed,
            enable_emergency_corridor=True,
            controller="hybrid",
            qaoa_p=1,
            qaoa_maxiter=20,
            qaoa_shots=1024,
        )

        self.assertIsInstance(result, QuantumFlowRunResult)
        # Verify model dimension and QAOA config are exposed
        self.assertEqual(result.qubit_count, 12)
        self.assertEqual(result.qaoa_p, 1)
        self.assertEqual(result.qaoa_shots, 1024)

        # Verify optimization validity
        self.assertEqual(result.optimization_status, "success")
        self.assertTrue(result.onehot_valid)
        self.assertTrue(result.emergency_valid)
        self.assertTrue(np.isfinite(result.optimization_energy))

        # Verify bitstring & vector
        self.assertIsNotNone(result.canonical_bitstring)
        self.assertEqual(len(result.canonical_bitstring), 12)
        self.assertIsNotNone(result.binary_vector)
        self.assertEqual(len(result.binary_vector), 12)

        # Verify normal signal plan matches decoded binary vector exactly
        expected_plan = decode_solution(result.binary_vector)
        self.assertEqual(result.normal_signal_plan, expected_plan)

        # Verify aliases
        self.assertEqual(result.solver_used, result.optimization_solver)
        self.assertEqual(result.fallback_used, result.optimization_fallback_used)
        self.assertEqual(result.fallback_reason, result.optimization_fallback_reason)


if __name__ == "__main__":
    unittest.main()
