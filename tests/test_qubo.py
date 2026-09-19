"""Unit tests for complete QUBO modeling, variable mappings, upper-triangular convention, energy evaluation, one-hot, traffic, coupling, emergency objectives, and exhaustive enumeration."""

import unittest
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
from optimization.qubo_model import (
    QUBOModel,
    qubo_energy,
)
from optimization.onehot import (
    DEFAULT_ONEHOT_PENALTY,
    evaluate_onehot_penalty,
    add_onehot_penalty,
    build_onehot_qubo,
)
from optimization.traffic_objectives import (
    TrafficObjectiveConfig,
    TrafficState,
    add_wait_term,
    add_capacity_term,
    add_throughput_term,
    add_traffic_terms,
    evaluate_wait,
    evaluate_capacity,
    evaluate_throughput,
    evaluate_local_traffic_qubo_energy,
)
from optimization.coupling import (
    CouplingConfig,
    DEFAULT_INTERSECTION_CAPACITY,
    validate_coupling_inputs,
    add_coupling_term,
    evaluate_coupling,
)
from optimization.emergency import (
    DEFAULT_EMERGENCY_WEIGHT,
    DEFAULT_FORCED_DURATION,
    EmergencyConstraints,
    add_emergency_term,
    evaluate_emergency,
    build_emergency_qubo,
)
from optimization.qubo_builder import (
    FullQUBOConfig,
    ComponentBreakdown,
    evaluate_components,
    build_qubo,
)
from optimization.enumeration import (
    StateRecord,
    ExhaustiveAnalysisResult,
    enumerate_qubo_states,
)
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    validate_solution,
    decode_solution,
)


class TestVariablesAndMapping(unittest.TestCase):
    """Test suite A: Validating canonical variable ordering and index lookups."""

    def test_variable_count_and_cardinality(self):
        """Verify exactly 4 intersections, 3 durations, and 12 total binary variables."""
        self.assertEqual(len(INTERSECTIONS), 4)
        self.assertEqual(len(DURATIONS), 3)
        self.assertEqual(NUM_VARIABLES, 12)
        self.assertEqual(len(VARIABLE_INDEX), 12)
        self.assertEqual(len(INDEX_TO_VARIABLE), 12)
        self.assertEqual(len(VARIABLE_NAMES), 12)

    def test_canonical_variable_indices(self):
        """Verify the exact required 12-variable ordering."""
        expected_mapping = {
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
        for (inter, dur), expected_idx in expected_mapping.items():
            self.assertEqual(VARIABLE_INDEX[(inter, dur)], expected_idx)
            self.assertEqual(INDEX_TO_VARIABLE[expected_idx], (inter, dur))
            self.assertEqual(get_variable_index(inter, dur), expected_idx)

    def test_intersection_subsets(self):
        """Verify helper retrieves the correct 3 consecutive indices per intersection."""
        self.assertEqual(get_intersection_variable_indices("I1"), [0, 1, 2])
        self.assertEqual(get_intersection_variable_indices("I2"), [3, 4, 5])
        self.assertEqual(get_intersection_variable_indices("I3"), [6, 7, 8])
        self.assertEqual(get_intersection_variable_indices("I4"), [9, 10, 11])

    def test_invalid_variable_lookups(self):
        """Verify invalid intersection or duration triggers KeyError."""
        with self.assertRaises(KeyError):
            get_variable_index("I5", 15)
        with self.assertRaises(KeyError):
            get_variable_index("I1", 60)
        with self.assertRaises(KeyError):
            get_intersection_variable_indices("I99")


class TestQUBOEnergyAndConvention(unittest.TestCase):
    """Test suite B & C: Validating Upper-Triangular QUBO energy calculation and convention."""

    def test_manual_2var_qubo_energies(self):
        """Verify explicit 2-variable test case: E(x) = 3*x0 + 5*x1 + 7*x0*x1."""
        Q = np.array([
            [3.0, 7.0],
            [0.0, 5.0],
        ], dtype=np.float64)

        self.assertAlmostEqual(qubo_energy(Q, [1, 1]), 15.0)
        self.assertAlmostEqual(qubo_energy(Q, [1, 0]), 3.0)
        self.assertAlmostEqual(qubo_energy(Q, [0, 1]), 5.0)
        self.assertAlmostEqual(qubo_energy(Q, [0, 0]), 0.0)

        Q_dict = {(0, 0): 3.0, (1, 1): 5.0, (0, 1): 7.0}
        self.assertAlmostEqual(qubo_energy(Q_dict, [1, 1]), 15.0)
        self.assertAlmostEqual(qubo_energy(Q_dict, [1, 0]), 3.0)
        self.assertAlmostEqual(qubo_energy(Q_dict, [0, 1]), 5.0)
        self.assertAlmostEqual(qubo_energy(Q_dict, [0, 0]), 0.0)

    def test_prevent_double_counting_and_enforce_upper_triangular(self):
        """Verify lower-triangular entries are strictly disallowed."""
        Q_invalid = np.array([
            [3.0, 3.5],
            [3.5, 5.0],
        ], dtype=np.float64)

        with self.assertRaises(ValueError):
            qubo_energy(Q_invalid, [1, 1])

        Q_dict_invalid = {(0, 0): 3.0, (1, 1): 5.0, (1, 0): 7.0}
        with self.assertRaises(ValueError):
            qubo_energy(Q_dict_invalid, [1, 1])

    def test_qubo_model_instantiation_and_energy(self):
        """Verify QUBOModel dataclass preserves offset and provides identical energy evaluation."""
        Q = np.array([
            [3.0, 7.0],
            [0.0, 5.0],
        ], dtype=np.float64)
        var_order = (("I1", 15), ("I1", 30))
        offset = 10.0
        metadata = {"test": True}

        model = QUBOModel(Q=Q, variable_order=var_order, offset=offset, metadata=metadata)

        self.assertEqual(model.num_variables, 2)
        self.assertEqual(model.offset, 10.0)
        self.assertEqual(model.metadata, {"test": True})

        self.assertAlmostEqual(model.energy([1, 1], include_offset=True), 25.0)
        self.assertAlmostEqual(model.energy([1, 1], include_offset=False), 15.0)
        self.assertAlmostEqual(model.energy([0, 0], include_offset=True), 10.0)
        self.assertAlmostEqual(model.energy([0, 0], include_offset=False), 0.0)

        d = model.to_dict()
        self.assertEqual(d, {(0, 0): 3.0, (0, 1): 7.0, (1, 1): 5.0})

    def test_invalid_state_vectors(self):
        """Verify non-binary values or dimension mismatches raise exceptions."""
        Q = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64)

        with self.assertRaises(ValueError):
            qubo_energy(Q, [1, 2])
        with self.assertRaises(ValueError):
            qubo_energy(Q, [1, -1])
        with self.assertRaises(ValueError):
            qubo_energy(Q, [1, 0, 1])


class TestOneHotPenalty(unittest.TestCase):
    """Test suite for Phase 3: One-Hot Quadratic Penalty Formulation and Validation."""

    def setUp(self):
        self.A = 50.0
        self.model = build_onehot_qubo(penalty_coefficient=self.A)

    def _make_state(self, i1_bits, i2_bits=(1, 0, 0), i3_bits=(1, 0, 0), i4_bits=(1, 0, 0)):
        return list(i1_bits) + list(i2_bits) + list(i3_bits) + list(i4_bits)

    def test_case_a_single_selection(self):
        for pattern in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            x = self._make_state(i1_bits=pattern, i2_bits=(0, 1, 0), i3_bits=(0, 0, 1), i4_bits=(1, 0, 0))
            direct_p = evaluate_onehot_penalty(x, penalty_coefficient=self.A)
            qubo_p = self.model.energy(x, include_offset=True)
            self.assertAlmostEqual(direct_p, 0.0)
            self.assertAlmostEqual(qubo_p, 0.0)

    def test_case_b_none_selected(self):
        x = self._make_state(i1_bits=(0, 0, 0), i2_bits=(1, 0, 0), i3_bits=(0, 1, 0), i4_bits=(0, 0, 1))
        direct_p = evaluate_onehot_penalty(x, penalty_coefficient=self.A)
        qubo_p = self.model.energy(x, include_offset=True)
        self.assertAlmostEqual(direct_p, self.A)
        self.assertAlmostEqual(qubo_p, self.A)

    def test_case_c_two_selected(self):
        for pattern in [(1, 1, 0), (1, 0, 1), (0, 1, 1)]:
            x = self._make_state(i1_bits=pattern, i2_bits=(1, 0, 0), i3_bits=(1, 0, 0), i4_bits=(1, 0, 0))
            direct_p = evaluate_onehot_penalty(x, penalty_coefficient=self.A)
            qubo_p = self.model.energy(x, include_offset=True)
            self.assertAlmostEqual(direct_p, self.A)
            self.assertAlmostEqual(qubo_p, self.A)

    def test_case_d_all_three_selected(self):
        x = self._make_state(i1_bits=(1, 1, 1), i2_bits=(1, 0, 0), i3_bits=(1, 0, 0), i4_bits=(1, 0, 0))
        direct_p = evaluate_onehot_penalty(x, penalty_coefficient=self.A)
        qubo_p = self.model.energy(x, include_offset=True)
        self.assertAlmostEqual(direct_p, 4.0 * self.A)
        self.assertAlmostEqual(qubo_p, 4.0 * self.A)

    def test_case_e_all_four_valid(self):
        x = [
            1, 0, 0,
            0, 1, 0,
            0, 0, 1,
            0, 1, 0,
        ]
        self.assertAlmostEqual(evaluate_onehot_penalty(x, self.A), 0.0)
        self.assertAlmostEqual(self.model.energy(x, include_offset=True), 0.0)

    def test_case_f_one_invalid_zero_selections(self):
        x = [
            1, 0, 0,
            0, 0, 0,
            0, 1, 0,
            0, 0, 1,
        ]
        self.assertAlmostEqual(evaluate_onehot_penalty(x, self.A), self.A)
        self.assertAlmostEqual(self.model.energy(x, include_offset=True), self.A)

    def test_case_g_one_invalid_two_selections(self):
        x = [
            1, 0, 0,
            1, 1, 0,
            0, 1, 0,
            0, 0, 1,
        ]
        self.assertAlmostEqual(evaluate_onehot_penalty(x, self.A), self.A)
        self.assertAlmostEqual(self.model.energy(x, include_offset=True), self.A)

    def test_case_h_one_invalid_three_selections(self):
        x = [
            1, 0, 0,
            1, 1, 1,
            0, 1, 0,
            0, 0, 1,
        ]
        self.assertAlmostEqual(evaluate_onehot_penalty(x, self.A), 4.0 * self.A)
        self.assertAlmostEqual(self.model.energy(x, include_offset=True), 4.0 * self.A)

    def test_matrix_structure_and_couplings(self):
        Q = self.model.Q
        A = self.A
        self.assertAlmostEqual(self.model.offset, 4.0 * A)

        for inter in INTERSECTIONS:
            indices = get_intersection_variable_indices(inter)
            for k in indices:
                self.assertAlmostEqual(Q[k, k], -A, msg=f"Diagonal failed at {k} ({inter})")
            for i_idx, k in enumerate(indices):
                for j in indices[i_idx + 1:]:
                    self.assertAlmostEqual(Q[k, j], 2.0 * A, msg=f"Intra-pair failed at ({k}, {j})")

        lower_tri = np.tril(Q, -1)
        self.assertTrue(np.allclose(lower_tri, 0.0), "Lower triangular entries must be 0")

        for inter1 in INTERSECTIONS:
            for inter2 in INTERSECTIONS:
                if inter1 != inter2:
                    indices1 = get_intersection_variable_indices(inter1)
                    indices2 = get_intersection_variable_indices(inter2)
                    for k in indices1:
                        for j in indices2:
                            self.assertAlmostEqual(
                                Q[min(k, j), max(k, j)],
                                0.0 if min(k, j) != max(k, j) else -A,
                                msg=f"Cross-intersection coupling found between {inter1} and {inter2} at ({k}, {j})",
                            )

    def test_exhaustive_single_intersection_all_8_states(self):
        A = self.A
        Q_single = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        Q_single, offset_single = add_onehot_penalty(Q_single, 0.0, penalty_coefficient=A, intersections=["I1"])
        model_single = QUBOModel(
            Q=Q_single,
            variable_order=tuple(INDEX_TO_VARIABLE[i] for i in range(NUM_VARIABLES)),
            offset=offset_single,
        )

        for bits in itertools.product([0, 1], repeat=3):
            x = list(bits) + [0] * 9
            direct = A * ((sum(bits) - 1.0) ** 2)
            qubo_val = model_single.energy(x, include_offset=True)
            self.assertAlmostEqual(direct, qubo_val)


class TestTrafficObjectives(unittest.TestCase):
    """Test suite for Phase 4: Local Traffic Objectives (H_wait, H_capacity, H_throughput)."""

    def setUp(self):
        self.config = TrafficObjectiveConfig(
            wait_weight=2.0,
            capacity_weight=10.0,
            capacity_threshold=0.7,
            throughput_weight=1.0,
            service_rate=1.0,
        )
        self.state_dict = {
            "I1": {"queue": 30.0, "density": 0.50, "capacity": 40.0},
            "I2": {"queue": 20.0, "density": 1.00, "capacity": 35.0},
            "I3": {"queue": 10.0, "density": 0.70, "capacity": 30.0},
            "I4": {"queue": 45.0, "density": 0.85, "capacity": 50.0},
        }
        self.traffic_state = TrafficState.from_dict(self.state_dict)

    def test_1_wait_diagonal_contributions(self):
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_wait_term(Q, self.traffic_state, self.config)

        self.assertAlmostEqual(Q[0, 0], 4.0)
        self.assertAlmostEqual(Q[1, 1], 2.0)
        self.assertAlmostEqual(Q[2, 2], 4.0 / 3.0)

        self.assertAlmostEqual(Q[3, 3], 2.0 * (20.0 / 15.0))
        self.assertAlmostEqual(Q[4, 4], 2.0 * (20.0 / 30.0))
        self.assertAlmostEqual(Q[5, 5], 2.0 * (20.0 / 45.0))

        self.assertAlmostEqual(Q[6, 6], 2.0 * (10.0 / 15.0))
        self.assertAlmostEqual(Q[7, 7], 2.0 * (10.0 / 30.0))
        self.assertAlmostEqual(Q[8, 8], 2.0 * (10.0 / 45.0))

        self.assertAlmostEqual(Q[9, 9], 2.0 * (45.0 / 15.0))
        self.assertAlmostEqual(Q[10, 10], 2.0 * (45.0 / 30.0))
        self.assertAlmostEqual(Q[11, 11], 2.0 * (45.0 / 45.0))

    def test_2_capacity_below_or_at_threshold(self):
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_capacity_term(Q, self.traffic_state, self.config)

        self.assertAlmostEqual(Q[0, 0], 0.0)
        self.assertAlmostEqual(Q[1, 1], 0.0)
        self.assertAlmostEqual(Q[2, 2], 0.0)

        self.assertAlmostEqual(Q[6, 6], 0.0)
        self.assertAlmostEqual(Q[7, 7], 0.0)
        self.assertAlmostEqual(Q[8, 8], 0.0)

    def test_3_capacity_above_threshold_ordering_and_exact_values(self):
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_capacity_term(Q, self.traffic_state, self.config)

        self.assertAlmostEqual(Q[3, 3], 90.0)
        self.assertAlmostEqual(Q[4, 4], 45.0)
        self.assertAlmostEqual(Q[5, 5], 0.0)
        self.assertTrue(Q[3, 3] > Q[4, 4] > Q[5, 5])

        self.assertAlmostEqual(Q[9, 9], 45.0)
        self.assertAlmostEqual(Q[10, 10], 22.5)
        self.assertAlmostEqual(Q[11, 11], 0.0)

    def test_4_and_5_throughput_negative_reward_and_saturation(self):
        cfg = TrafficObjectiveConfig(throughput_weight=2.0, service_rate=1.0)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_throughput_term(Q, self.traffic_state, cfg)

        self.assertAlmostEqual(Q[3, 3], -30.0)
        self.assertAlmostEqual(Q[4, 4], -40.0)
        self.assertAlmostEqual(Q[5, 5], -40.0)

    def test_6_no_off_diagonal_terms(self):
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_traffic_terms(Q, self.traffic_state, self.config)

        off_diag = Q - np.diag(np.diag(Q))
        self.assertTrue(np.allclose(off_diag, 0.0), "Traffic terms must NOT generate off-diagonal entries.")

    def test_7_component_additivity_and_energy_equivalence(self):
        Q_onehot = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        Q_onehot, off_onehot = add_onehot_penalty(Q_onehot, 0.0, penalty_coefficient=50.0)

        Q_wait = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_wait_term(Q_wait, self.traffic_state, self.config)

        Q_cap = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_capacity_term(Q_cap, self.traffic_state, self.config)

        Q_tp = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_throughput_term(Q_tp, self.traffic_state, self.config)

        Q_total = Q_onehot + Q_wait + Q_cap + Q_tp
        total_offset = off_onehot

        x = [
            0, 1, 0,
            0, 0, 1,
            1, 0, 0,
            0, 1, 0,
        ]

        direct_onehot = evaluate_onehot_penalty(x, penalty_coefficient=50.0)
        direct_w = evaluate_wait(x, self.traffic_state, self.config)
        direct_c = evaluate_capacity(x, self.traffic_state, self.config)
        direct_t = evaluate_throughput(x, self.traffic_state, self.config)
        expected_total = direct_onehot + direct_w + direct_c - direct_t

        matrix_total = qubo_energy(Q_total, x) + total_offset
        self.assertAlmostEqual(matrix_total, expected_total)

    def test_8_offset_invariance(self):
        x_zeros = [0] * NUM_VARIABLES
        Q_traffic = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_traffic_terms(Q_traffic, self.traffic_state, self.config)
        self.assertAlmostEqual(qubo_energy(Q_traffic, x_zeros), 0.0)

    def test_9_randomized_deterministic_cross_checks(self):
        rng = np.random.default_rng(seed=42)

        for trial in range(10):
            rand_state = TrafficState(
                queues={inter: float(rng.uniform(0, 50)) for inter in INTERSECTIONS},
                densities={inter: float(rng.uniform(0.0, 1.2)) for inter in INTERSECTIONS},
            )
            rand_cfg = TrafficObjectiveConfig(
                wait_weight=float(rng.uniform(0.5, 5.0)),
                capacity_weight=float(rng.uniform(5.0, 20.0)),
                capacity_threshold=0.7,
                throughput_weight=float(rng.uniform(0.5, 3.0)),
                service_rate=1.0,
            )

            rand_x = rng.choice([0, 1], size=NUM_VARIABLES).tolist()

            Q_w = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
            add_wait_term(Q_w, rand_state, rand_cfg)
            self.assertAlmostEqual(qubo_energy(Q_w, rand_x), evaluate_wait(rand_x, rand_state, rand_cfg))

            Q_c = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
            add_capacity_term(Q_c, rand_state, rand_cfg)
            self.assertAlmostEqual(qubo_energy(Q_c, rand_x), evaluate_capacity(rand_x, rand_state, rand_cfg))

            Q_tp = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
            add_throughput_term(Q_tp, rand_state, rand_cfg)
            self.assertAlmostEqual(qubo_energy(Q_tp, rand_x), -evaluate_throughput(rand_x, rand_state, rand_cfg))

            Q_all = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
            add_traffic_terms(Q_all, rand_state, rand_cfg)
            self.assertAlmostEqual(
                qubo_energy(Q_all, rand_x),
                evaluate_local_traffic_qubo_energy(rand_x, rand_state, rand_cfg),
            )


class TestCouplingObjectives(unittest.TestCase):
    """Test suite for Phase 5: Inter-Intersection Coupling Penalty (H_coupling)."""

    def setUp(self):
        self.state_dict = {
            "I1": {"queue": 15.0, "density": 0.30, "capacity": 50.0},
            "I2": {"queue": 20.0, "density": 0.40, "capacity": 100.0},
            "I3": {"queue": 30.0, "density": 0.60, "capacity": 50.0},
            "I4": {"queue": 10.0, "density": 0.25, "capacity": 40.0},
        }
        self.traffic_state = TrafficState.from_dict(self.state_dict)
        self.edges = [("I1", "I2"), ("I1", "I3"), ("I2", "I4"), ("I3", "I4")]

    def test_1_manual_coefficient_calculation(self):
        cfg = CouplingConfig(coupling_weight=9.0)
        edges = [("I1", "I2")]
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q, edges, self.traffic_state, cfg)

        idx_i1_30 = get_variable_index("I1", 30)
        idx_i2_15 = get_variable_index("I2", 15)
        self.assertEqual(idx_i1_30, 1)
        self.assertEqual(idx_i2_15, 3)
        self.assertAlmostEqual(Q[1, 3], 0.8)

    def test_2_downstream_45s_duration_is_zero(self):
        cfg = CouplingConfig(coupling_weight=5.0)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q, self.edges, self.traffic_state, cfg)

        for src, dst in self.edges:
            idx_dst_45 = get_variable_index(dst, 45)
            for t_src in DURATIONS:
                idx_src = get_variable_index(src, t_src)
                row, col = min(idx_src, idx_dst_45), max(idx_src, idx_dst_45)
                self.assertAlmostEqual(Q[row, col], 0.0)

    def test_3_directionality(self):
        cfg = CouplingConfig(coupling_weight=9.0)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q, [("I1", "I2")], self.traffic_state, cfg)

        idx_i1_45 = get_variable_index("I1", 45)
        idx_i2_15 = get_variable_index("I2", 15)
        self.assertAlmostEqual(Q[2, 3], 1.2)

    def test_4_self_loop_rejection(self):
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("I1", "I1")], self.traffic_state)

        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        with self.assertRaises(ValueError):
            add_coupling_term(Q, [("I1", "I1")], self.traffic_state)

    def test_5_unknown_intersection_rejection(self):
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("I1", "I5")], self.traffic_state)
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("X1", "I2")], self.traffic_state)

    def test_6_and_7_zero_or_negative_capacity_rejection(self):
        state_zero_cap = TrafficState(queues={"I1": 10, "I2": 20}, densities={}, capacities={"I2": 0.0})
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("I1", "I2")], state_zero_cap)

        state_neg_cap = TrafficState(queues={"I1": 10, "I2": 20}, densities={}, capacities={"I2": -10.0})
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("I1", "I2")], state_neg_cap)

    def test_8_negative_queue_rejection(self):
        state_neg_q = TrafficState(queues={"I1": 10, "I2": -5.0}, densities={}, capacities={"I2": 50.0})
        with self.assertRaises(ValueError):
            validate_coupling_inputs([("I1", "I2")], state_neg_q)

    def test_9_and_10_upper_triangular_and_zero_diagonals(self):
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q, self.edges, self.traffic_state, CouplingConfig(coupling_weight=5.0))

        self.assertTrue(np.allclose(np.diag(Q), 0.0))
        lower_tri = np.tril(Q, -1)
        self.assertTrue(np.allclose(lower_tri, 0.0))
        upper_tri = np.triu(Q, 1)
        self.assertTrue(np.any(upper_tri > 0.0))

    def test_11_direct_vs_qubo_energy_equivalence(self):
        cfg = CouplingConfig(coupling_weight=7.5)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q, self.edges, self.traffic_state, cfg)

        test_states = [
            [0, 0, 1,   1, 0, 0,   0, 1, 0,   1, 0, 0],
            [1, 0, 0,   0, 0, 1,   0, 0, 1,   0, 0, 1],
            [0, 1, 0,   0, 1, 0,   0, 1, 0,   0, 1, 0],
        ]

        for x in test_states:
            direct_val = evaluate_coupling(x, self.edges, self.traffic_state, cfg)
            matrix_val = qubo_energy(Q, x)
            self.assertAlmostEqual(direct_val, matrix_val)

    def test_12_multiple_directed_edges_independence(self):
        cfg = CouplingConfig(coupling_weight=5.0)

        Q_e1 = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q_e1, [("I1", "I2")], self.traffic_state, cfg)

        Q_e2 = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q_e2, [("I2", "I4")], self.traffic_state, cfg)

        Q_both = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q_both, [("I1", "I2"), ("I2", "I4")], self.traffic_state, cfg)

        self.assertTrue(np.allclose(Q_e1 + Q_e2, Q_both))

    def test_13_additivity_with_traffic_and_onehot(self):
        A = 50.0
        cfg_traffic = TrafficObjectiveConfig(wait_weight=2.0, capacity_weight=10.0, throughput_weight=1.0)
        cfg_coupling = CouplingConfig(coupling_weight=5.0)

        Q_onehot = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        Q_onehot, offset = add_onehot_penalty(Q_onehot, 0.0, penalty_coefficient=A)

        Q_traffic = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_traffic_terms(Q_traffic, self.traffic_state, cfg_traffic)

        Q_coupling = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q_coupling, self.edges, self.traffic_state, cfg_coupling)

        Q_total = Q_onehot + Q_traffic + Q_coupling

        x = [
            0, 0, 1,
            1, 0, 0,
            0, 1, 0,
            0, 0, 1,
        ]

        direct_onehot = evaluate_onehot_penalty(x, penalty_coefficient=A)
        direct_traffic = evaluate_local_traffic_qubo_energy(x, self.traffic_state, cfg_traffic)
        direct_coupling = evaluate_coupling(x, self.edges, self.traffic_state, cfg_coupling)
        expected_total = direct_onehot + direct_traffic + direct_coupling

        matrix_total = qubo_energy(Q_total, x) + offset
        self.assertAlmostEqual(matrix_total, expected_total)

    def test_14_randomized_deterministic_cross_checks(self):
        rng = np.random.default_rng(seed=123)

        all_possible_edges = [
            (src, dst) for src in INTERSECTIONS for dst in INTERSECTIONS if src != dst
        ]

        for trial in range(10):
            num_edges = int(rng.integers(2, 6))
            edge_indices = rng.choice(len(all_possible_edges), size=num_edges, replace=False)
            rand_edges = [all_possible_edges[idx] for idx in edge_indices]

            rand_state = TrafficState(
                queues={inter: float(rng.uniform(0, 40)) for inter in INTERSECTIONS},
                densities={inter: float(rng.uniform(0.1, 1.0)) for inter in INTERSECTIONS},
                capacities={inter: float(rng.uniform(20, 80)) for inter in INTERSECTIONS},
            )
            rand_cfg = CouplingConfig(coupling_weight=float(rng.uniform(1.0, 10.0)))
            rand_x = rng.choice([0, 1], size=NUM_VARIABLES).tolist()

            Q_c = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
            add_coupling_term(Q_c, rand_edges, rand_state, rand_cfg)

            direct_c = evaluate_coupling(rand_x, rand_edges, rand_state, rand_cfg)
            matrix_c = qubo_energy(Q_c, rand_x)
            self.assertAlmostEqual(direct_c, matrix_c)


class TestEmergencyObjectives(unittest.TestCase):
    """Test suite for Phase 6: Emergency Constraint Interface and Objective Term (H_emergency)."""

    def test_1_basic_route_matrix_and_offset(self):
        em = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        offset = 0.0
        Q, offset = add_emergency_term(Q, offset, em)

        self.assertAlmostEqual(offset, 150.0)

        idx_i2_45 = get_variable_index("I2", 45)
        idx_i3_45 = get_variable_index("I3", 45)
        idx_i4_45 = get_variable_index("I4", 45)

        self.assertEqual(idx_i2_45, 5)
        self.assertEqual(idx_i3_45, 8)
        self.assertEqual(idx_i4_45, 11)

        self.assertAlmostEqual(Q[5, 5], -50.0)
        self.assertAlmostEqual(Q[8, 8], -50.0)
        self.assertAlmostEqual(Q[11, 11], -50.0)

        diag_copy = np.diag(Q).copy()
        diag_copy[5] = 0.0
        diag_copy[8] = 0.0
        diag_copy[11] = 0.0
        self.assertTrue(np.allclose(diag_copy, 0.0))

        off_diag = Q - np.diag(np.diag(Q))
        self.assertTrue(np.allclose(off_diag, 0.0))

    def test_2_fully_compliant_state(self):
        em = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        model = build_emergency_qubo(em)

        x = [
            1, 0, 0,
            0, 0, 1,
            0, 0, 1,
            0, 0, 1,
        ]

        direct_val = evaluate_emergency(x, em)
        qubo_val = model.energy(x, include_offset=True)

        self.assertAlmostEqual(direct_val, 0.0)
        self.assertAlmostEqual(qubo_val, 0.0)

    def test_3_one_violation(self):
        em = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        model = build_emergency_qubo(em)

        x = [
            1, 0, 0,
            0, 1, 0,
            0, 0, 1,
            0, 0, 1,
        ]

        direct_val = evaluate_emergency(x, em)
        qubo_val = model.energy(x, include_offset=True)

        self.assertAlmostEqual(direct_val, 50.0)
        self.assertAlmostEqual(qubo_val, 50.0)

    def test_4_three_violations(self):
        em = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        model = build_emergency_qubo(em)

        x = [
            1, 0, 0,
            1, 0, 0,
            0, 1, 0,
            1, 0, 0,
        ]

        direct_val = evaluate_emergency(x, em)
        qubo_val = model.energy(x, include_offset=True)

        self.assertAlmostEqual(direct_val, 150.0)
        self.assertAlmostEqual(qubo_val, 150.0)

    def test_5_other_duration_incurs_penalty(self):
        em = EmergencyConstraints(route=["I1"], forced_duration=45, emergency_weight=60.0)
        model = build_emergency_qubo(em)

        x_15 = [1, 0, 0,   1, 0, 0,   1, 0, 0,   1, 0, 0]
        self.assertAlmostEqual(model.energy(x_15, include_offset=True), 60.0)

        x_30 = [0, 1, 0,   1, 0, 0,   1, 0, 0,   1, 0, 0]
        self.assertAlmostEqual(model.energy(x_30, include_offset=True), 60.0)

        x_45 = [0, 0, 1,   1, 0, 0,   1, 0, 0,   1, 0, 0]
        self.assertAlmostEqual(model.energy(x_45, include_offset=True), 0.0)

    def test_6_generic_forced_duration_30(self):
        em = EmergencyConstraints(route=["I1", "I3"], forced_duration=30, emergency_weight=40.0)
        Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        offset = 0.0
        Q, offset = add_emergency_term(Q, offset, em)

        idx_i1_30 = get_variable_index("I1", 30)
        idx_i3_30 = get_variable_index("I3", 30)

        self.assertAlmostEqual(offset, 80.0)
        self.assertAlmostEqual(Q[1, 1], -40.0)
        self.assertAlmostEqual(Q[7, 7], -40.0)

        x_comp = [0, 1, 0,   1, 0, 0,   0, 1, 0,   1, 0, 0]
        self.assertAlmostEqual(evaluate_emergency(x_comp, em), 0.0)
        self.assertAlmostEqual(qubo_energy(Q, x_comp) + offset, 0.0)

    def test_7_invalid_forced_duration_rejection(self):
        for invalid_dur in [0, 10, 20, 60, -45, "45"]:
            with self.assertRaises(ValueError):
                EmergencyConstraints(route=["I1"], forced_duration=invalid_dur)

    def test_8_unknown_route_intersection_rejection(self):
        with self.assertRaises(ValueError):
            EmergencyConstraints(route=["I1", "I5"])
        with self.assertRaises(ValueError):
            EmergencyConstraints(route=["X1", "I2"])

    def test_9_duplicate_route_intersection_rejection(self):
        with self.assertRaises(ValueError):
            EmergencyConstraints(route=["I1", "I2", "I1"])
        with self.assertRaises(ValueError):
            EmergencyConstraints(route=["I3", "I3"])

    def test_10_empty_route_rejection(self):
        with self.assertRaises(ValueError):
            EmergencyConstraints(route=[])

    def test_11_direct_vs_qubo_equivalence_all_permutations(self):
        em = EmergencyConstraints(route=["I1", "I2", "I4"], forced_duration=45, emergency_weight=75.0)
        model = build_emergency_qubo(em)

        for _ in range(20):
            rand_x = np.random.choice([0, 1], size=NUM_VARIABLES).tolist()
            direct_val = evaluate_emergency(rand_x, em)
            matrix_val = model.energy(rand_x, include_offset=True)
            self.assertAlmostEqual(direct_val, matrix_val)

    def test_12_and_13_no_off_diagonal_and_exact_diagonals(self):
        em = EmergencyConstraints(route=["I2", "I4"], forced_duration=15, emergency_weight=35.0)
        model = build_emergency_qubo(em)
        Q = model.Q

        off_diag = Q - np.diag(np.diag(Q))
        self.assertTrue(np.allclose(off_diag, 0.0), "Emergency QUBO must have zero off-diagonals.")

        idx_i2_15 = get_variable_index("I2", 15)
        idx_i4_15 = get_variable_index("I4", 15)

        for k in range(NUM_VARIABLES):
            if k in (idx_i2_15, idx_i4_15):
                self.assertAlmostEqual(Q[k, k], -35.0)
            else:
                self.assertAlmostEqual(Q[k, k], 0.0)

    def test_14_full_system_additive_composition(self):
        A = 50.0
        cfg_traffic = TrafficObjectiveConfig(wait_weight=2.0, capacity_weight=10.0, throughput_weight=1.0)
        cfg_coupling = CouplingConfig(coupling_weight=5.0)
        state = TrafficState.from_dict({
            "I1": {"queue": 20, "density": 0.5, "capacity": 50},
            "I2": {"queue": 30, "density": 0.8, "capacity": 40},
            "I3": {"queue": 15, "density": 0.4, "capacity": 40},
            "I4": {"queue": 25, "density": 0.6, "capacity": 50},
        })
        edges = [("I1", "I2"), ("I2", "I4"), ("I3", "I4")]
        em = EmergencyConstraints(route=["I1", "I2", "I4"], forced_duration=45, emergency_weight=60.0)

        Q_onehot = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        Q_onehot, off_onehot = add_onehot_penalty(Q_onehot, 0.0, penalty_coefficient=A)

        Q_traffic = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_traffic_terms(Q_traffic, state, cfg_traffic)

        Q_coupling = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        add_coupling_term(Q_coupling, edges, state, cfg_coupling)

        Q_emergency = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
        Q_emergency, off_emergency = add_emergency_term(Q_emergency, 0.0, em)

        Q_total = Q_onehot + Q_traffic + Q_coupling + Q_emergency
        total_offset = off_onehot + off_emergency

        x_comp = [
            0, 0, 1,
            0, 0, 1,
            1, 0, 0,
            0, 0, 1,
        ]

        direct_onehot = evaluate_onehot_penalty(x_comp, penalty_coefficient=A)
        direct_traffic = evaluate_local_traffic_qubo_energy(x_comp, state, cfg_traffic)
        direct_coupling = evaluate_coupling(x_comp, edges, state, cfg_coupling)
        direct_emergency = evaluate_emergency(x_comp, em)
        expected_total = direct_onehot + direct_traffic + direct_coupling + direct_emergency

        matrix_total = qubo_energy(Q_total, x_comp) + total_offset
        self.assertAlmostEqual(matrix_total, expected_total)
        self.assertAlmostEqual(direct_emergency, 0.0)

        x_viol = [
            0, 0, 1,
            1, 0, 0,
            1, 0, 0,
            0, 0, 1,
        ]
        direct_viol_em = evaluate_emergency(x_viol, em)
        self.assertAlmostEqual(direct_viol_em, 60.0)
        matrix_viol_total = qubo_energy(Q_total, x_viol) + total_offset
        expected_viol_total = (
            evaluate_onehot_penalty(x_viol, penalty_coefficient=A)
            + evaluate_local_traffic_qubo_energy(x_viol, state, cfg_traffic)
            + evaluate_coupling(x_viol, edges, state, cfg_coupling)
            + direct_viol_em
        )
        self.assertAlmostEqual(matrix_viol_total, expected_viol_total)

    def test_15_randomized_deterministic_validation(self):
        rng = np.random.default_rng(seed=999)

        for trial in range(10):
            k = int(rng.integers(1, 4))
            route = list(rng.choice(list(INTERSECTIONS), size=k, replace=False))
            forced_dur = int(rng.choice(list(DURATIONS)))
            F = float(rng.uniform(10.0, 100.0))

            em = EmergencyConstraints(route=route, forced_duration=forced_dur, emergency_weight=F)
            model = build_emergency_qubo(em)

            rand_x = rng.choice([0, 1], size=NUM_VARIABLES).tolist()

            direct_em = evaluate_emergency(rand_x, em)
            matrix_em = model.energy(rand_x, include_offset=True)

            self.assertAlmostEqual(direct_em, matrix_em)


class TestCompleteQUBOAndEnumeration(unittest.TestCase):
    """Test suite for Phase 7: Complete QUBO Assembly, Exhaustive Enumeration, and Global Diagnostics."""

    def setUp(self):
        self.state_dict = {
            "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
            "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
            "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
            "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
        }
        self.traffic_state = TrafficState.from_dict(self.state_dict)
        self.edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
        self.emergency = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        self.config = FullQUBOConfig(
            onehot_penalty=100.0,
            wait_weight=2.0,
            capacity_weight=10.0,
            capacity_threshold=0.7,
            throughput_weight=1.0,
            service_rate=1.0,
            coupling_weight=5.0,
            default_capacity=100.0,
            emergency_weight=50.0,
        )

    def test_1_qubo_dimensions_and_structure(self):
        """TEST 1: Complete QUBO model must have shape (12, 12) and upper-triangular form."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        self.assertEqual(model.Q.shape, (12, 12))
        self.assertEqual(model.num_variables, 12)

        lower_tri = np.tril(model.Q, -1)
        self.assertTrue(np.allclose(lower_tri, 0.0), "Complete QUBO Q must be strictly upper-triangular.")

    def test_2_offset_composition(self):
        """TEST 2: Offset equals one-hot offset (4*100 = 400) + emergency offset (3*50 = 150) = 550."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        self.assertAlmostEqual(model.offset, 550.0)

        # Without emergency, offset must be exactly 400.0
        model_no_em = build_qubo(self.traffic_state, self.edges, self.config, emergency_constraints=None)
        self.assertAlmostEqual(model_no_em.offset, 400.0)

    def test_3_direct_vs_qubo_total_energy_identity(self):
        """TEST 3: For arbitrary binary states, evaluate_components(x).total == model.energy(x)."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        rng = np.random.default_rng(seed=777)

        for _ in range(25):
            rand_x = rng.choice([0, 1], size=NUM_VARIABLES).tolist()
            breakdown = evaluate_components(
                x=rand_x,
                traffic_state=self.traffic_state,
                edges=self.edges,
                config=self.config,
                emergency_constraints=self.emergency,
            )
            matrix_energy = model.energy(rand_x, include_offset=True)
            self.assertAlmostEqual(breakdown.total, matrix_energy)

    def test_4_exhaustive_enumeration_counts(self):
        """TEST 4: Exhaustive state space has exactly 4096 states, exactly 81 one-hot valid, and 3 emergency valid."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        res = enumerate_qubo_states(model, self.traffic_state, self.edges, self.config, self.emergency)

        self.assertEqual(res.total_states_count, 4096)
        self.assertEqual(res.onehot_valid_count, 81)  # 3^4 = 81
        self.assertEqual(res.emergency_valid_count, 3)  # 3^(4-3) = 3^1 = 3

    def test_5_emergency_valid_counts_for_different_route_lengths(self):
        """TEST 5: Verify emergency valid count = 3^(4-m) for routes of length m = 1, 2, 3."""
        # m = 1 (route: ["I1"]) -> 3^(4-1) = 27
        em1 = EmergencyConstraints(route=["I1"], forced_duration=45)
        m1 = build_qubo(self.traffic_state, self.edges, self.config, em1)
        r1 = enumerate_qubo_states(m1, self.traffic_state, self.edges, self.config, em1)
        self.assertEqual(r1.emergency_valid_count, 27)

        # m = 2 (route: ["I1", "I2"]) -> 3^(4-2) = 9
        em2 = EmergencyConstraints(route=["I1", "I2"], forced_duration=45)
        m2 = build_qubo(self.traffic_state, self.edges, self.config, em2)
        r2 = enumerate_qubo_states(m2, self.traffic_state, self.edges, self.config, em2)
        self.assertEqual(r2.emergency_valid_count, 9)

        # m = 3 (route: ["I1", "I2", "I3"]) -> 3^(4-3) = 3
        em3 = EmergencyConstraints(route=["I1", "I2", "I3"], forced_duration=45)
        m3 = build_qubo(self.traffic_state, self.edges, self.config, em3)
        r3 = enumerate_qubo_states(m3, self.traffic_state, self.edges, self.config, em3)
        self.assertEqual(r3.emergency_valid_count, 3)

    def test_6_best_valid_state_identification(self):
        """TEST 6: Analysis cleanly identifies best one-hot and best emergency valid states."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        res = enumerate_qubo_states(model, self.traffic_state, self.edges, self.config, self.emergency)

        self.assertIsNotNone(res.best_unconstrained)
        self.assertIsNotNone(res.best_onehot_valid)
        self.assertIsNotNone(res.best_emergency_valid)

        # Best one-hot valid must have valid signal plan
        self.assertTrue(res.best_onehot_valid.is_valid_onehot)
        self.assertIn("I1", res.best_onehot_valid.signal_plan)
        self.assertIn("I2", res.best_onehot_valid.signal_plan)
        self.assertIn("I3", res.best_onehot_valid.signal_plan)
        self.assertIn("I4", res.best_onehot_valid.signal_plan)

        # Best emergency valid must satisfy emergency corridor (I2=45, I3=45, I4=45)
        plan_em = res.best_emergency_valid.signal_plan
        self.assertEqual(plan_em["I2"], 45)
        self.assertEqual(plan_em["I3"], 45)
        self.assertEqual(plan_em["I4"], 45)

    def test_7_component_breakdown_consistency(self):
        """TEST 7: Check that component breakdown sums exactly to total."""
        model = build_qubo(self.traffic_state, self.edges, self.config, self.emergency)
        # Test state
        x = [0, 0, 1,   0, 0, 1,   0, 0, 1,   0, 0, 1]
        comp = evaluate_components(x, self.traffic_state, self.edges, self.config, self.emergency)

        calc_sum = (
            comp.onehot
            + comp.wait
            + comp.capacity
            - comp.throughput_reward
            + comp.coupling
            + comp.emergency
        )
        self.assertAlmostEqual(comp.total, calc_sum)
        self.assertAlmostEqual(comp.throughput_cost, -comp.throughput_reward)


if __name__ == "__main__":
    unittest.main()
