"""QuantumFlow Optimization Module.

Authoritative package for QUBO modeling, QAOA solving via Qiskit Aer,
Classical Simulated Annealing baseline, and solution decoding/validation.
"""

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
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    validate_solution,
    decode_solution,
)
from optimization.enumeration import (
    StateRecord,
    ExhaustiveAnalysisResult,
    enumerate_qubo_states,
)
from optimization.ising_converter import (
    bits_to_spins,
    spins_to_bits,
    IsingModel,
    ising_energy,
    qubo_to_ising,
    ising_to_qiskit_operator,
)
from optimization.qaoa_solver import (
    qiskit_bitstring_to_bits,
    bits_to_qiskit_bitstring,
    TinyQAOAResult,
    build_qaoa_circuit,
    solve_tiny_qaoa,
)
from optimization.production_qaoa import (
    ProductionQAOAResult,
    solve_production_qaoa,
)
from optimization.sa_solver import (
    qubo_to_bqm,
    SimulatedAnnealingResult,
    solve_simulated_annealing,
)
from optimization.hybrid_solver import (
    HybridSolveResult,
    solve_hybrid,
)
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

__all__ = [
    "INTERSECTIONS",
    "DURATIONS",
    "NUM_VARIABLES",
    "VARIABLE_INDEX",
    "INDEX_TO_VARIABLE",
    "VARIABLE_NAMES",
    "get_variable_index",
    "get_intersection_variable_indices",
    "QUBOModel",
    "qubo_energy",
    "DEFAULT_ONEHOT_PENALTY",
    "evaluate_onehot_penalty",
    "add_onehot_penalty",
    "build_onehot_qubo",
    "TrafficObjectiveConfig",
    "TrafficState",
    "add_wait_term",
    "add_capacity_term",
    "add_throughput_term",
    "add_traffic_terms",
    "evaluate_wait",
    "evaluate_capacity",
    "evaluate_throughput",
    "evaluate_local_traffic_qubo_energy",
    "CouplingConfig",
    "DEFAULT_INTERSECTION_CAPACITY",
    "validate_coupling_inputs",
    "add_coupling_term",
    "evaluate_coupling",
    "DEFAULT_EMERGENCY_WEIGHT",
    "DEFAULT_FORCED_DURATION",
    "EmergencyConstraints",
    "add_emergency_term",
    "evaluate_emergency",
    "build_emergency_qubo",
    "FullQUBOConfig",
    "ComponentBreakdown",
    "evaluate_components",
    "build_qubo",
    "is_valid_onehot",
    "is_valid_emergency",
    "validate_solution",
    "decode_solution",
    "StateRecord",
    "ExhaustiveAnalysisResult",
    "enumerate_qubo_states",
    "bits_to_spins",
    "spins_to_bits",
    "IsingModel",
    "ising_energy",
    "qubo_to_ising",
    "ising_to_qiskit_operator",
    "qiskit_bitstring_to_bits",
    "bits_to_qiskit_bitstring",
    "TinyQAOAResult",
    "build_qaoa_circuit",
    "solve_tiny_qaoa",
    "ProductionQAOAResult",
    "solve_production_qaoa",
    "qubo_to_bqm",
    "SimulatedAnnealingResult",
    "solve_simulated_annealing",
    "HybridSolveResult",
    "solve_hybrid",
    "BaseController",
    "ControllerOutput",
    "HybridController",
    "SimulatedAnnealingController",
    "FixedTimeController",
    "RuleBasedController",
    "signal_plan_to_binary_vector",
    "OptimizationMetrics",
    "TrafficMetrics",
    "TrialResult",
    "MetricSummary",
    "calculate_metric_summary",
    "summarize_results",
    "BenchmarkScenario",
    "create_deterministic_scenario",
    "create_random_scenario",
    "run_benchmark",
    "save_results_json",
    "load_results_json",
    "format_comparison_table",
]



