"""Tests for the multi-ambulance, arbiter, Pareto, hardware-comparison and Belagavi upgrades.

Covers regressions found while auditing the upgrade branch:
- the conflict QUBO used to ignore its delay/priority term (energy 0, arbitrary order);
- opposing-direction ambulance routes used to crash the simulator;
- the Pareto sweep used to be flat because preemption had no civilian cost.
"""

import importlib.util
import pytest

from optimization.emergency_conflict import (
    EmergencyConflictRequest as Req,
    arbitrate_conflict,
    build_conflict_qubo,
    decode_conflict_sequence,
    requests_from_configs,
    solve_emergency_conflict,
)
from optimization.ibm_hardware import compare_simulator_vs_hardware
from optimization.pareto import sweep_pareto_frontier
from optimization.solver_arbiter import (
    ArbiterComparisonResult,
    SolverCandidateRecord,
    describe_arbiter_outcome,
)
from simulation import belagavi
from simulation.emergency_controller import EmergencyCorridorController
from simulation.engine import TrafficSimulator
from simulation.integration import run_quantumflow_demo
from simulation.scenario import create_canonical_scenarios

PLAN = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}


def _two_requests():
    return [
        Req("A", ("I1", "I2", "I3"), "I1", 2, 20, priority_level=1),
        Req("B", ("I4", "I3", "I2"), "I4", 1, 22, priority_level=2),
    ]


# ------------------------------------------------------------------ conflict QUBO
def test_conflict_qubo_has_real_objective_and_prefers_priority_order():
    reqs = _two_requests()
    qubo = build_conflict_qubo(reqs, "I3")
    a_first = (1, 0, 0, 1)  # A slot0, B slot1
    b_first = (0, 1, 1, 0)
    assert qubo.energy(a_first) < qubo.energy(b_first)
    assert qubo.energy(a_first) > 0.0  # delay term is actually present

    sched = solve_emergency_conflict(reqs, "I3", current_time=15)
    assert sched.sequenced_vehicles == ["A", "B"]


def test_conflict_qubo_invalid_assignments_are_never_cheaper_than_valid_ones():
    qubo = build_conflict_qubo(_two_requests(), "I3")
    valid = min(qubo.energy(x) for x in [(1, 0, 0, 1), (0, 1, 1, 0)])
    for bits in range(16):
        x = tuple((bits >> i) & 1 for i in range(4))
        if decode_conflict_sequence(x, 2) is None:
            assert qubo.energy(x) > valid


@pytest.mark.parametrize("solver", ["sa", "greedy", "exact"])
def test_solve_emergency_conflict_solver_options(solver):
    sched = solve_emergency_conflict(_two_requests(), "I3", current_time=0, solver=solver)
    assert sorted(sched.sequenced_vehicles) == ["A", "B"]
    assert sched.is_feasible


def test_solve_emergency_conflict_rejects_unknown_solver():
    with pytest.raises(ValueError):
        solve_emergency_conflict(_two_requests(), "I3", current_time=0, solver="magic")


def test_arbiter_reports_a_loser_honestly():
    """Priority-1 vehicle arrives late: Greedy (priority first) is suboptimal, exact/SA are not."""
    reqs = [
        Req("LATE_P1", ("I1", "I2", "I3"), "I1", 2, 40, priority_level=1),
        Req("EARLY_P2", ("I4", "I3", "I2"), "I4", 1, 20, priority_level=2),
    ]
    res = arbitrate_conflict(reqs, "I3", include_qaoa=False)
    assert res.records["sa"].is_optimal
    assert not res.records["greedy"].is_optimal
    assert res.records["greedy"].energy > res.exact_energy
    assert res.winner == "sa"
    assert "did worse" in res.verdict


def test_arbiter_with_qaoa_returns_valid_records_and_ground_truth():
    res = arbitrate_conflict(_two_requests(), "I3", qaoa_shots=1024, qaoa_maxiter=30)
    assert set(res.records) == {"qaoa", "sa", "greedy"}
    assert res.num_qubits == 4
    for rec in res.records.values():
        assert rec.energy >= res.exact_energy - 1e-9  # nobody can beat exact enumeration
    assert res.records["sa"].is_valid and res.records["greedy"].is_valid


def test_arbiter_size_limits():
    with pytest.raises(ValueError):
        arbitrate_conflict(_two_requests()[:1], "I3")
    many = [Req(f"V{i}", ("I1", "I2", "I3"), "I1", 1, 10 + i) for i in range(5)]
    with pytest.raises(ValueError):
        arbitrate_conflict(many, "I3")


def test_requests_from_configs_only_includes_routes_through_junction():
    sc = create_canonical_scenarios()["scenario_f_three_emergency_conflict"]
    at_i4 = requests_from_configs(sc.get_all_emergency_configs(), "I4")
    assert sorted(r.vehicle_id for r in at_i4) == ["AMB_2", "FIRE_3"]  # AMB_1 (I1->I3) never reaches I4
    at_i3 = requests_from_configs(sc.get_all_emergency_configs(), "I3")
    assert len(at_i3) == 3
    assert {r.priority_level for r in at_i3} == {1, 2, 3}


def test_describe_arbiter_outcome_states_qaoa_loss_and_ties():
    def rec(name, e):
        return SolverCandidateRecord(name, "0" * 12, {"I1": 30}, e, 0.1, True, True, True)

    def build(qe, se, ge):
        cands = {"qaoa": rec("qaoa", qe), "sa": rec("sa", se), "greedy": rec("greedy", ge)}
        return ArbiterComparisonResult(cands, "sa", {}, min(qe, se, ge), qe, se, ge, 0.1, 0.1, 0.1, qe - se, qe - ge)

    assert "QAOA lost" in describe_arbiter_outcome(build(-10.0, -12.0, -11.0))
    assert "tied" in describe_arbiter_outcome(build(-5.0, -5.0, -5.0))
    won = describe_arbiter_outcome(build(-20.0, -12.0, -11.0))
    assert "QAOA won" in won and "lost" not in won


# ------------------------------------------------------------------ simulator
def test_reverse_route_is_valid_but_zigzag_is_not():
    ctrl = EmergencyCorridorController()
    ctrl.validate_route(("I4", "I3", "I2"))
    ctrl.validate_route(("I1", "I2", "I3"))
    with pytest.raises(ValueError):
        ctrl.validate_route(("I1", "I3", "I2"))
    with pytest.raises(ValueError):
        ctrl.validate_route(("I1", "I2", "I1"))


def test_scenario_e_runs_and_corridor_speeds_up_both_ambulances():
    sc = create_canonical_scenarios()["scenario_e_two_emergency_conflict"]
    off = TrafficSimulator(sc, enable_emergency_corridor=False).simulate(PLAN, seed=7)
    on = TrafficSimulator(sc, enable_emergency_corridor=True).simulate(PLAN, seed=7)
    assert len(on.emergency_vehicle_results) == 2
    assert on.resolved_emergency_conflicts >= 1
    by_id = {r["vehicle_id"]: r for r in on.emergency_vehicle_results}
    assert by_id["AMB_EAST"]["priority"] == 1 and by_id["AMB_WEST"]["priority"] == 2
    assert all(r["completed"] for r in on.emergency_vehicle_results)
    off_rt = {r["vehicle_id"]: r["response_time"] for r in off.emergency_vehicle_results}
    for vid, r in by_id.items():
        assert r["response_time"] < (off_rt[vid] if off_rt[vid] is not None else 1e9)


def test_scenario_f_three_ambulances_all_complete_without_deadlock():
    sc = create_canonical_scenarios()["scenario_f_three_emergency_conflict"]
    m = TrafficSimulator(sc, enable_emergency_corridor=True).simulate(PLAN, seed=3)
    assert m.active_emergencies_count == 3
    assert all(r["completed"] for r in m.emergency_vehicle_results)


def test_conflict_schedule_is_deterministic_for_same_seed():
    sc = create_canonical_scenarios()["scenario_e_two_emergency_conflict"]
    a = TrafficSimulator(sc, enable_emergency_corridor=True).simulate(PLAN, seed=11)
    b = TrafficSimulator(sc, enable_emergency_corridor=True).simulate(PLAN, seed=11)
    assert a.emergency_vehicle_results == b.emergency_vehicle_results


def test_cross_street_traffic_is_opt_in_and_preemption_costs_it_delay():
    import dataclasses

    base = create_canonical_scenarios()["scenario_d_single_emergency"]
    assert TrafficSimulator(base).simulate(PLAN, seed=1).cross_street_vehicles == 0

    sc = dataclasses.replace(base, cross_street_rates={i: 0.4 for i in base.intersections})
    low = TrafficSimulator(sc, enable_emergency_corridor=True, preemption_duty=0.2).simulate(PLAN, seed=1)
    high = TrafficSimulator(sc, enable_emergency_corridor=True, preemption_duty=1.0).simulate(PLAN, seed=1)
    assert low.cross_street_vehicles > 0
    assert high.cross_street_person_delay > low.cross_street_person_delay
    assert high.emergency_response_time <= low.emergency_response_time


def test_run_result_exposes_people_fairness_and_multi_emergency_fields():
    sc = create_canonical_scenarios()["scenario_e_two_emergency_conflict"]
    res = run_quantumflow_demo(scenario=sc, seed=5, controller="sa")
    d = res.to_dict()
    assert d["emergency_present"] is True
    assert d["active_emergencies_count"] == 2
    assert len(d["emergency_vehicle_results"]) == 2
    assert 0.0 < d["jain_fairness_index"] <= 1.0
    assert d["total_person_delay"] > 0
    assert d["estimated_co2_kg"] > 0


# ------------------------------------------------------------------ Pareto
def test_pareto_trade_off_is_real_when_cross_traffic_is_heavy():
    sc = create_canonical_scenarios()["scenario_d_single_emergency"]
    fr = sweep_pareto_frontier(sc, lambda_values=(0.0, 0.5, 1.0), seed=42, qaoa_shots=128, cross_street_rate=0.5)
    lo, mid, hi = fr.points
    assert lo.preemption_duty == 0.0 and hi.preemption_duty == 1.0
    assert hi.mean_emergency_response_time < lo.mean_emergency_response_time
    assert hi.cross_street_person_delay > lo.cross_street_person_delay
    assert hi.arterial_person_delay < lo.arterial_person_delay  # delay moves off the arterial...
    # ...onto the cross streets; the *total* is close to flat, so it is not asserted.
    assert hi.person_delay == pytest.approx(hi.arterial_person_delay + hi.cross_street_person_delay)
    assert fr.cross_street_rate == 0.5
    assert {p.lambda_param for p in fr.dominated_free()} <= {0.0, 0.5, 1.0}


# ------------------------------------------------------------------ hardware comparison
def test_hardware_comparison_offline_by_default_and_noise_moves_distribution():
    res = compare_simulator_vs_hardware(_two_requests(), shots=512)
    assert set(res.runs) == {"ideal", "noisy"}
    assert not res.hardware_requested and "not requested" in res.hardware_status
    assert res.runs["ideal"].tvd_vs_ideal == 0.0
    assert res.runs["noisy"].tvd_vs_ideal > 0.0
    assert res.runs["ideal"].shots == 512
    assert "no quantum advantage" in res.honesty_note
    assert res.exact_sequence == ["A", "B"]


@pytest.mark.skipif(importlib.util.find_spec("qiskit_ibm_runtime") is not None, reason="runtime installed")
def test_hardware_request_without_runtime_degrades_gracefully():
    res = compare_simulator_vs_hardware(_two_requests(), shots=256, use_hardware=True)
    assert "hardware" not in res.runs
    assert "unavailable" in res.hardware_status


def test_hardware_comparison_rejects_bad_sizes():
    with pytest.raises(ValueError):
        compare_simulator_vs_hardware(_two_requests()[:1])


# ------------------------------------------------------------------ Belagavi twin
def test_belagavi_twin_scenarios_and_labels():
    assert belagavi.junction_name("I3") == "RPD Cross"
    assert belagavi.junction_name("ZZ") == "ZZ"
    assert "I4" in belagavi.label_route(("I4", "I3")) or "Tilakwadi" in belagavi.label_route(("I4", "I3"))
    for kind in ("normal", "peak", "peak_two_ambulances"):
        sc = belagavi.belagavi_scenario(kind)
        sc.validate_plan(PLAN)
    two = belagavi.belagavi_scenario("peak_two_ambulances")
    assert len(two.get_all_emergency_configs()) == 2
    with pytest.raises(ValueError):
        belagavi.belagavi_scenario("nonsense")


def test_belagavi_twin_carries_simulation_disclaimer():
    info = belagavi.describe()
    assert "not a validated model" in info["disclaimer"]
    assert all(j["lat"] is None and j["lon"] is None for j in info["junctions"])  # no invented coordinates
    m = TrafficSimulator(belagavi.belagavi_scenario("peak_two_ambulances"), enable_emergency_corridor=True).simulate(PLAN, seed=2)
    assert m.active_emergencies_count == 2
