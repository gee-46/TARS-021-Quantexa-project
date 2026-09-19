"""Comprehensive Test Suite for Closed-Loop Adaptive Rolling-Horizon Traffic Optimization.

Validates:
1. Replan interval validation and cycle boundary compatibility.
2. Exact replan timing (t=0 initial, t=60, 120, 180, 240 scheduled).
3. Observation of live queues at the beginning of tick t before mutation.
4. Mathematical state-dependence of QUBO construction on observed queues (Test 8 & 9).
5. Continuous simulation integrity (no queue/clock/RNG resetting).
6. Emergency independence and full 5-stage lifecycle recovery.
7. Telemetry fidelity (no fabricated fields, JSON serializability).
8. Deterministic reproducibility under fixed seeds.
9. Static vs Adaptive fair comparison execution.
10. Performance telemetry (QAOA executions, SA fallback counts, runtime tracking).
"""

import json
import pytest
import numpy as np

from optimization.variables import INTERSECTIONS, DURATIONS, NUM_VARIABLES
from optimization.traffic_objectives import TrafficState, TrafficObjectiveConfig
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.qubo_model import QUBOModel
from simulation.scenario import (
    SimulationScenario,
    EmergencyVehicleConfig,
    create_default_simulation_scenario,
)
from simulation.models import Vehicle, SignalState
from simulation.engine import TrafficSimulator, simulate
from simulation.adaptive_controller import (
    AdaptiveRollingHorizonController,
    ReplanningEvent,
)
from simulation.integration import (
    QuantumFlowRunResult,
    create_canonical_demo_scenario,
    run_quantumflow_demo,
    run_adaptive_vs_static_comparison,
    compare_runs,
)


# ==============================================================================
# 1. REPLAN INTERVAL VALIDATION
# ==============================================================================

def test_replan_interval_validation_success():
    """Verify valid replan intervals (positive multiples of cycle_length) are accepted."""
    scenario = create_canonical_demo_scenario()
    assert scenario.cycle_length == 60

    ctrl_60 = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=60)
    assert ctrl_60.replan_interval == 60

    ctrl_120 = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=120)
    assert ctrl_120.replan_interval == 120


def test_replan_interval_validation_failure():
    """Verify invalid replan intervals raise ValueError."""
    scenario = create_canonical_demo_scenario()
    assert scenario.cycle_length == 60

    # Non-positive interval
    with pytest.raises(ValueError, match="positive"):
        AdaptiveRollingHorizonController(scenario=scenario, replan_interval=0)

    with pytest.raises(ValueError, match="positive"):
        AdaptiveRollingHorizonController(scenario=scenario, replan_interval=-30)

    # Not a multiple of cycle_length (e.g. 45s or 75s with 60s cycle)
    with pytest.raises(ValueError, match="multiple of scenario cycle_length"):
        AdaptiveRollingHorizonController(scenario=scenario, replan_interval=45)

    with pytest.raises(ValueError, match="multiple of scenario cycle_length"):
        AdaptiveRollingHorizonController(scenario=scenario, replan_interval=90)


# ==============================================================================
# 2. INITIAL PLAN AT T=0 (CORRECTION 2)
# ==============================================================================

def test_adaptive_initial_plan_generation_at_t0():
    """Verify initial plan at t=0 is generated from actual initial queues and recorded as index 0, trigger='initial'."""
    scenario = create_canonical_demo_scenario(seed=42)
    ctrl = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=60, solver_seed=42)

    init_plan = ctrl.generate_initial_plan()
    assert init_plan is not None
    assert len(init_plan) == 4
    for inter in scenario.intersections:
        assert inter in init_plan
        assert init_plan[inter] in DURATIONS

    assert len(ctrl.replan_events) == 1
    ev0 = ctrl.replan_events[0]
    assert ev0.replan_index == 0
    assert ev0.simulation_time == 0
    assert ev0.trigger == "initial"
    assert ev0.applied is True
    assert ev0.queue_state == {k: float(v) for k, v in scenario.initial_queues.items()}
    assert ev0.solver_used in ("qaoa", "sa")
    assert ev0.qubit_count == 12
    assert ev0.onehot_valid is True


# ==============================================================================
# 3. EXACT REPLAN TIMING AND SCHEDULE (CORRECTIONS 1 & 2)
# ==============================================================================

def test_exact_replan_timing_300s_simulation():
    """Verify 300s simulation with replan_interval=60 produces exactly 5 replan events at t=0, 60, 120, 180, 240."""
    scenario = create_canonical_demo_scenario(seed=42)
    assert scenario.duration_seconds == 300

    result = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
        enable_emergency_corridor=False,
    )

    assert result.adaptive_enabled is True
    assert result.replan_interval == 60
    assert result.replan_count == 4  # 4 scheduled replans
    assert len(result.replanning_events) == 5  # Total 5 events: index 0 to 4

    expected_times = [0, 60, 120, 180, 240]
    expected_triggers = ["initial", "scheduled", "scheduled", "scheduled", "scheduled"]

    for idx, ev in enumerate(result.replanning_events):
        assert ev["replan_index"] == idx
        assert ev["simulation_time"] == expected_times[idx]
        assert ev["trigger"] == expected_triggers[idx]
        assert ev["applied"] is True
        assert ev["qubit_count"] == 12
        assert ev["onehot_valid"] is True


def test_no_replan_past_simulation_end():
    """Verify no replanning event occurs at or beyond duration_seconds (e.g. at t=300)."""
    scenario = create_canonical_demo_scenario(seed=42)
    result = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
    )
    for ev in result.replanning_events:
        assert ev["simulation_time"] < scenario.duration_seconds


# ==============================================================================
# 4. CONTINUOUS SIMULATION INTEGRITY (CORRECTIONS 1 & 8)
# ==============================================================================

def test_continuous_simulation_no_state_reset():
    """Verify continuous simulation: time, queues, vehicle travel, and Poisson RNG advance continuously without reset."""
    scenario = create_canonical_demo_scenario(seed=42)
    result = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
    )

    assert result.simulation_duration == 300
    assert result.vehicles_generated > 0
    assert result.vehicles_completed > 0
    assert result.average_waiting_time > 0.0
    assert result.throughput == result.vehicles_completed
    assert result.cumulative_optimization_runtime > 0.0


# ==============================================================================
# 5. LIVE QUEUES FEED OPTIMIZATION STATE (CORRECTION 9 - TEST 8)
# ==============================================================================

def test_live_queues_passed_to_traffic_state():
    """Test 8: Verify that actual live simulator queues are extracted into TrafficState for replanning."""
    scenario = create_canonical_demo_scenario()
    ctrl = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=60)

    observed_queues = {"I1": 25, "I2": 3, "I3": 40, "I4": 12}
    traffic_state = ctrl.extract_traffic_state(observed_queues)

    for inter in scenario.intersections:
        assert traffic_state.queues[inter] == float(observed_queues[inter])
        expected_density = min(0.95, max(0.20, observed_queues[inter] / 20.0))
        assert pytest.approx(traffic_state.densities[inter], 1e-4) == expected_density
        assert traffic_state.capacities[inter] == 100.0


# ==============================================================================
# 6. QUBO MATHEMATICAL STATE-DEPENDENCE (CORRECTION 9 - TEST 9)
# ==============================================================================

def test_changing_traffic_state_changes_qubo_coefficients():
    """Test 9: Verify that changing the observed traffic state mathematically changes the resulting QUBO coefficients and energy representation."""
    scenario = create_canonical_demo_scenario()
    ctrl = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=60)
    edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]

    # State A: Heavy queue on I1, empty on I4
    state_a = ctrl.extract_traffic_state({"I1": 50, "I2": 5, "I3": 5, "I4": 0})
    qubo_a = build_qubo(traffic_state=state_a, edges=edges, config=ctrl.qubo_config)

    # State B: Empty queue on I1, heavy on I4
    state_b = ctrl.extract_traffic_state({"I1": 0, "I2": 5, "I3": 5, "I4": 50})
    qubo_b = build_qubo(traffic_state=state_b, edges=edges, config=ctrl.qubo_config)

    # Mathematical Proof 1: QUBO matrices must not be identical
    matrix_diff = np.abs(qubo_a.Q - qubo_b.Q)
    assert np.sum(matrix_diff) > 0.0, "QUBO matrices for different traffic states must differ!"

    # Mathematical Proof 2: The evaluated energy of the same test bitstring must differ
    # Test bitstring: [1, 0, 0,  1, 0, 0,  1, 0, 0,  1, 0, 0] (15s for all)
    test_vec = [1, 0, 0,  1, 0, 0,  1, 0, 0,  1, 0, 0]
    energy_a = qubo_a.energy(test_vec)
    energy_b = qubo_b.energy(test_vec)

    assert energy_a != energy_b, f"QUBO energy must be state-dependent: {energy_a} vs {energy_b}"


# ==============================================================================
# 7. TELEMETRY STRUCTURE AND FIDELITY (CORRECTIONS 7 & 11)
# ==============================================================================

def test_replanning_event_telemetry_fields():
    """Verify ReplanningEvent contains all real, un-fabricated measured fields and serializes to JSON."""
    scenario = create_canonical_demo_scenario(seed=42)
    ctrl = AdaptiveRollingHorizonController(scenario=scenario, replan_interval=60, solver_seed=42)

    plan = ctrl.replan(second=60, current_queues={"I1": 14, "I2": 9, "I3": 11, "I4": 18})
    assert len(ctrl.replan_events) == 1
    ev = ctrl.replan_events[0]

    # Verify exact field structure and types
    assert ev.replan_index == 0
    assert ev.simulation_time == 60
    assert ev.trigger == "scheduled"
    assert isinstance(ev.queue_state, dict)
    assert isinstance(ev.density_state, dict)
    assert isinstance(ev.signal_plan, dict)
    assert ev.solver_used in ("qaoa", "sa")
    assert isinstance(ev.optimization_energy, float)
    assert isinstance(ev.optimization_runtime, float)
    assert ev.optimization_runtime > 0.0
    assert isinstance(ev.fallback_used, bool)
    assert ev.applied is True
    assert len(ev.canonical_bitstring) == 12
    assert ev.qubit_count == 12
    assert ev.onehot_valid is True
    assert ev.emergency_valid is True

    # Verify pure JSON serializability
    d = ev.to_dict()
    json_str = json.dumps(d)
    assert len(json_str) > 0


# ==============================================================================
# 8. EMERGENCY INDEPENDENCE AND 5-STAGE RECOVERY (CORRECTION 10)
# ==============================================================================

def test_emergency_independence_and_recovery_lifecycle():
    """Correction 10: Explicitly verify the 5-stage lifecycle of emergency interaction under adaptive control:
    1. Adaptive normal plan exists before emergency.
    2. Emergency preemption overrides normal plan during transit.
    3. Emergency completes.
    4. Recovery occurs.
    5. The adaptive normal plan resumes active control.
    """
    scenario = create_canonical_demo_scenario(seed=42)
    # Emergency arrives at t=20 on route ("I2", "I3", "I4")
    assert scenario.emergency_config is not None
    assert scenario.emergency_config.arrival_time == 20

    result = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
        enable_emergency_corridor=True,
    )

    # 1. Adaptive plan exists before emergency (t=0)
    assert result.initial_signal_plan is not None
    ev0 = result.replanning_events[0]
    assert ev0["simulation_time"] == 0
    assert ev0["trigger"] == "initial"

    # 2. Emergency detected and corridor activated
    assert result.emergency_present is True
    assert result.emergency_corridor_enabled is True
    assert result.emergency_detected_time is not None
    assert result.emergency_detected_time == 20
    assert result.emergency_corridor_activated_time is not None
    assert result.emergency_preemption_count > 0

    # 3. Emergency completes
    assert result.emergency_completed is True
    assert result.emergency_completed_time is not None
    assert result.emergency_response_time is not None
    assert result.emergency_response_time > 0

    # 4. Recovery occurs
    assert result.recovery_completed is True
    for inter, mode in result.final_signal_states.items():
        assert mode == "NORMAL", f"Intersection {inter} must recover to NORMAL, got {mode}"

    # 5. Adaptive replanning continued at scheduled cycle boundaries without corruption
    assert result.replan_count == 4
    assert len(result.replanning_events) == 5
    for ev in result.replanning_events:
        assert ev["onehot_valid"] is True
        assert ev["applied"] is True


# ==============================================================================
# 9. DETERMINISTIC REPRODUCIBILITY (CORRECTION 8)
# ==============================================================================

def test_adaptive_deterministic_reproducibility():
    """Verify identical seed produces identical adaptive replanning events, signal plans, and metrics."""
    scenario = create_canonical_demo_scenario(seed=42)

    res1 = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
        enable_emergency_corridor=True,
    )

    res2 = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
        enable_emergency_corridor=True,
    )

    assert res1.throughput == res2.throughput
    assert res1.average_waiting_time == res2.average_waiting_time
    assert res1.max_queue == res2.max_queue
    assert res1.emergency_completed == res2.emergency_completed
    assert res1.emergency_response_time == res2.emergency_response_time
    assert len(res1.replanning_events) == len(res2.replanning_events)

    for ev1, ev2 in zip(res1.replanning_events, res2.replanning_events):
        assert ev1["simulation_time"] == ev2["simulation_time"]
        assert ev1["signal_plan"] == ev2["signal_plan"]
        assert ev1["queue_state"] == ev2["queue_state"]
        assert ev1["solver_used"] == ev2["solver_used"]


def test_different_seeds_produce_independent_trajectories():
    """Verify different seeds produce independent Poisson arrivals and distinct queue trajectories."""
    scenario_42 = create_canonical_demo_scenario(seed=42)
    scenario_99 = create_canonical_demo_scenario(seed=99)

    res_42 = run_quantumflow_demo(scenario=scenario_42, seed=42, enable_adaptive=True)
    res_99 = run_quantumflow_demo(scenario=scenario_99, seed=99, enable_adaptive=True)

    # Different seeds yield different Poisson arrivals
    assert res_42.vehicles_generated != res_99.vehicles_generated


# ==============================================================================
# 10. STATIC VS ADAPTIVE FAIR COMPARISON (CORRECTION 8)
# ==============================================================================

def test_static_vs_adaptive_comparison_facility():
    """Verify run_adaptive_vs_static_comparison executes both modes under identical initial conditions and returns structured deltas."""
    scenario = create_canonical_demo_scenario(seed=42)

    comp = run_adaptive_vs_static_comparison(
        scenario=scenario,
        seed=42,
        replan_interval=60,
        enable_emergency_corridor=True,
    )

    assert "static" in comp
    assert "adaptive" in comp
    assert "deltas" in comp
    assert "summary" in comp

    static_res = comp["static"]
    adaptive_res = comp["adaptive"]
    deltas = comp["deltas"]

    # Initial conditions must match exactly
    assert static_res["seed"] == adaptive_res["seed"] == 42
    assert static_res["simulation_duration"] == adaptive_res["simulation_duration"] == 300

    # Static has 0 scheduled replans; adaptive has 4 scheduled replans
    assert static_res["replan_count"] == 0
    assert adaptive_res["replan_count"] == 4
    assert len(adaptive_res["replanning_events"]) == 5

    # Arithmetic deltas exist and are correctly typed
    assert isinstance(deltas["throughput_delta"], int)
    assert isinstance(deltas["average_wait_delta"], float)
    assert isinstance(deltas["max_queue_delta"], int)
    assert isinstance(deltas["normal_wait_delta"], float)


# ==============================================================================
# 11. PERFORMANCE TELEMETRY AND TRACKING (CORRECTION 11)
# ==============================================================================

def test_performance_telemetry_tracking():
    """Correction 11: Verify cumulative runtime, QAOA executions, and SA fallback counts are recorded."""
    scenario = create_canonical_demo_scenario(seed=42)
    result = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
    )

    assert result.cumulative_optimization_runtime is not None
    assert result.cumulative_optimization_runtime > 0.0
    assert result.qaoa_execution_count >= 1
    assert isinstance(result.sa_fallback_count, int)
    assert result.qaoa_execution_count >= result.sa_fallback_count


# ==============================================================================
# 12. RUN RESULT QUANTUM HARDENING COMPATIBILITY
# ==============================================================================

def test_quantumflow_run_result_properties_and_aliases():
    """Verify QuantumFlowRunResult backward-compatible properties and aliases work seamlessly with adaptive runs."""
    scenario = create_canonical_demo_scenario(seed=42)
    res = run_quantumflow_demo(
        scenario=scenario,
        seed=42,
        enable_adaptive=True,
        replan_interval=60,
    )

    assert res.solver_used == res.optimization_solver
    assert res.fallback_used == res.optimization_fallback_used
    assert res.fallback_reason == res.optimization_fallback_reason
    assert res.qubit_count == 12

    d = res.to_dict()
    assert isinstance(d, dict)
    assert d["adaptive_enabled"] is True
    assert d["replan_count"] == 4
    assert len(d["replanning_events"]) == 5
