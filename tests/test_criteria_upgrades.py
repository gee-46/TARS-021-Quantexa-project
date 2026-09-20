"""Tests for the criteria-closing upgrades: cross-street-aware QUBO term, queue-aware route planning, emissions/baselines via the API."""

import dataclasses

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api_server
from optimization.qubo_builder import CROSS_STREET_WEIGHT, FullQUBOConfig, build_qubo
from optimization.variables import DURATIONS, INTERSECTIONS, get_variable_index
from simulation.adaptive_controller import AdaptiveRollingHorizonController
from simulation.registry import all_scenarios
from simulation.route_planner import build_graph, expected_queue_delay, plan_route

client = TestClient(api_server.app)


# ------------------------------------------------------------------ cross-street QUBO term
def _state(cross=None):
    st = {i: {"queue": 20.0, "density": 0.5} for i in INTERSECTIONS}
    if cross:
        for i in INTERSECTIONS:
            st[i]["cross_rate"] = cross
    return st


def test_cross_street_term_is_off_by_default_and_changes_nothing():
    base = build_qubo(_state(), None, config=FullQUBOConfig())
    with_rate_but_weight_zero = build_qubo(_state(cross=0.4), None, config=FullQUBOConfig(cross_street_weight=0.0))
    assert np.array_equal(base.Q, with_rate_but_weight_zero.Q)
    # weight on but no rates given: still nothing
    assert np.array_equal(base.Q, build_qubo(_state(), None, config=FullQUBOConfig(cross_street_weight=1.0)).Q)


def test_cross_street_term_matches_formula_and_penalises_long_greens_more():
    off = build_qubo(_state(cross=0.25), None, config=FullQUBOConfig(cross_street_weight=0.0))
    on = build_qubo(_state(cross=0.25), None, config=FullQUBOConfig(cross_street_weight=0.5))
    delta = {}
    for d in DURATIONS:
        k = get_variable_index("I2", d)
        delta[d] = on.Q[k, k] - off.Q[k, k]
        assert delta[d] == pytest.approx(0.5 * (0.25 * 60.0) / (60.0 - d))  # X * lambda*C / (C - t)
    assert delta[15] < delta[30] < delta[45]  # more arterial green leaves the cross street less of the cycle
    assert np.allclose(on.Q, np.triu(on.Q))  # still an upper-triangular QUBO


def test_cross_street_term_prevents_the_heavy_cross_traffic_failure():
    """With heavy cross demand the old objective picks 45 s everywhere (nearly doubling total delay); the new one does not."""
    from optimization.sa_solver import solve_sa
    from simulation.engine import TrafficSimulator

    d = all_scenarios()["scenario_d_single_emergency"]
    sc = dataclasses.replace(d, cross_street_rates={i: 0.5 for i in d.intersections})
    st = {i: {"queue": float(sc.initial_queues.get(i, 10)), "density": 0.3, "cross_rate": 0.5} for i in sc.intersections}

    def plan(w):
        return dict(solve_sa(build_qubo(st, None, config=FullQUBOConfig(cross_street_weight=w)), num_reads=60, num_sweeps=600, seed=42).signal_plan)

    def total_delay(pl):
        m = TrafficSimulator(sc).simulate(pl, seed=42)
        return m.total_person_delay + m.cross_street_person_delay

    old, new = plan(0.0), plan(CROSS_STREET_WEIGHT)
    assert set(old.values()) == {45}  # the old objective ignores the cross street
    assert total_delay(new) < 0.75 * total_delay(old)


def test_adaptive_controller_turns_the_cross_term_on_only_for_cross_traffic_scenarios():
    scs = all_scenarios()
    assert AdaptiveRollingHorizonController(scs["scenario_a_balanced"]).qubo_config.cross_street_weight == 0.0
    assert AdaptiveRollingHorizonController(scs["belagavi_peak"]).qubo_config.cross_street_weight == CROSS_STREET_WEIGHT
    ctrl = AdaptiveRollingHorizonController(scs["belagavi_peak"])
    state = ctrl.extract_traffic_state({"I1": 10, "I2": 10, "I3": 10, "I4": 10})
    assert state.cross_rates == {"I1": 0.20, "I2": 0.25, "I3": 0.25, "I4": 0.15}


# ------------------------------------------------------------------ route planner
def test_queue_delay_formula():
    assert expected_queue_delay(0, 30, 60) == 0.0
    assert expected_queue_delay(10, 30, 60) == pytest.approx(20.0)  # 10 veh, half the cycle green, 1 veh/s
    assert expected_queue_delay(10, 15, 60, service_rate=2.0) == pytest.approx(20.0)


def test_planner_returns_the_unique_arterial_path_in_both_directions():
    g = build_graph(["I1", "I2", "I3", "I4"])
    fwd = plan_route(g, "I1", "I3", {"I2": 10, "I3": 20}, {"I1": 30, "I2": 30, "I3": 30, "I4": 30})
    assert fwd.path == ["I1", "I2", "I3"] and fwd.unique_path and fwd.alternatives == []
    assert fwd.free_flow_seconds == 4.0
    assert fwd.junction_delay == {"I2": pytest.approx(20.0), "I3": pytest.approx(40.0)}
    assert fwd.expected_total_seconds == pytest.approx(4.0 + 60.0)
    rev = plan_route(g, "I4", "I2", {}, {"I2": 30, "I3": 30, "I4": 30})
    assert rev.path == ["I4", "I3", "I2"]


def test_planner_really_chooses_between_routes_on_a_richer_graph():
    """A bypass I1-I4 exists: it wins when the arterial junctions are congested and loses when they are clear."""
    g = build_graph(["I1", "I2", "I3", "I4"], edges=[("I1", "I2"), ("I2", "I3"), ("I3", "I4"), ("I1", "I4")])
    plan = {i: 30 for i in ["I1", "I2", "I3", "I4"]}
    clear = plan_route(g, "I1", "I3", {"I2": 0, "I3": 0, "I4": 0}, plan)
    assert clear.path == ["I1", "I2", "I3"]  # 2 hops beat the 3-hop detour via I4
    jammed = plan_route(g, "I1", "I3", {"I2": 40, "I3": 0, "I4": 0}, plan)
    assert jammed.path == ["I1", "I4", "I3"]  # detours around the jammed I2
    assert not jammed.unique_path and jammed.alternatives[0]["path"] == ["I1", "I2", "I3"]


def test_planner_rejects_bad_input():
    g = build_graph(["I1", "I2", "I3"])
    with pytest.raises(ValueError):
        plan_route(g, "I1", "I1", {}, {})
    with pytest.raises(ValueError):
        plan_route(g, "I1", "ZZ", {}, {})


# ------------------------------------------------------------------ API
def test_route_plan_endpoint_plans_then_simulates_the_corridor():
    body = {"scenario": "scenario_e_two_emergency_conflict", "origin": "I1", "destination": "I3", "seed": 42}
    r = client.post("/api/route-plan", json=body).json()
    assert r["route"]["path"] == ["I1", "I2", "I3"] and r["route"]["unique_path"] is True
    off, on = r["without_corridor"], r["with_corridor"]
    assert off["completed"] and on["completed"]
    assert on["response_time"] < off["response_time"]  # the corridor speeds up the dispatched ambulance
    assert "planning estimate" in r["note"]
    assert client.post("/api/route-plan", json=body).json() == r  # deterministic
    rev = client.post("/api/route-plan", json={**body, "origin": "I4", "destination": "I2"}).json()
    assert rev["route"]["path"] == ["I4", "I3", "I2"] and rev["with_corridor"]["response_time"] < rev["without_corridor"]["response_time"]


def test_route_plan_endpoint_validation():
    base = {"scenario": "scenario_a_balanced", "origin": "I1", "destination": "I3"}
    assert client.post("/api/route-plan", json={**base, "origin": "I3"}).status_code == 422
    assert client.post("/api/route-plan", json={**base, "destination": "I9"}).status_code == 422
    assert client.post("/api/route-plan", json={**base, "scenario": "nope"}).status_code == 404


def test_optimize_endpoint_reports_rule_based_reference_and_cross_street_term():
    plain = client.post("/api/optimize", json={"scenario": "scenario_a_balanced", "qaoa_maxiter": 8}).json()
    assert plain["cross_street_term"] is False and plain["qubo"]["weights"]["cross_street_weight"] == 0.0
    assert plain["rule_based"]["plan"] and "estimated_co2_kg" in plain["rule_based"]["metrics"]
    cross = client.post("/api/optimize", json={"scenario": "belagavi_peak", "qaoa_maxiter": 8}).json()
    assert cross["cross_street_term"] is True and cross["qubo"]["weights"]["cross_street_weight"] == CROSS_STREET_WEIGHT
    for run in (cross["baseline"], cross["optimized"]):
        m = run["metrics"]
        assert m["estimated_fuel_liters"] > 0 and m["estimated_co2_kg"] > 0
        assert m["cross_street_waiting_time"] > 0  # cross-street idling is counted in emissions
