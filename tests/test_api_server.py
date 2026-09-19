"""HTTP API tests: the React control center's backend must return real module output and reject bad input."""

import json
import math

import pytest
from fastapi.testclient import TestClient

import api_server
from simulation.registry import all_scenarios

client = TestClient(api_server.app)


def _no_nonfinite(obj):
    if isinstance(obj, float):
        assert math.isfinite(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _no_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _no_nonfinite(v)


def test_health_declares_simulator_only():
    r = client.get("/api/health").json()
    assert r["status"] == "online"
    assert "simulator" in r["quantum_backend"].lower()
    assert r["real_hardware_reachable_via_api"] is False


def test_scenarios_listing_matches_registry():
    r = client.get("/api/scenarios").json()
    assert {s["id"] for s in r} == set(all_scenarios())
    belagavi = [s for s in r if s["belagavi_inspired"]]
    assert belagavi and all("illustrative" in s["title"].lower() for s in belagavi)


def test_network_is_the_real_four_junction_arterial():
    r = client.get("/api/network", params={"scenario": "scenario_e_two_emergency_conflict"}).json()
    assert [n["id"] for n in r["nodes"]] == ["I1", "I2", "I3", "I4"]
    assert [(e["from"], e["to"]) for e in r["edges"]] == [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
    assert len(r["ambulances"]) == 2
    assert r["disclaimer"] is None  # canonical scenario: no Belagavi framing
    b = client.get("/api/network", params={"scenario": "belagavi_peak"}).json()
    assert "not a digital twin" in b["disclaimer"]
    assert b["nodes"][2]["name"] == "RPD Cross"


def test_unknown_scenario_is_404():
    assert client.get("/api/network", params={"scenario": "nope"}).status_code == 404
    assert client.post("/api/simulate", json={"scenario": "nope"}).status_code == 404


def test_simulate_returns_real_metrics_and_per_approach_stats():
    r = client.post("/api/simulate", json={"scenario": "scenario_d_single_emergency", "seed": 42, "corridor": True}).json()
    m = r["metrics"]
    assert r["plan"] == {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
    assert m["throughput"] > 0 and 0 < m["jain_fairness_index"] <= 1
    assert set(m["approach_mean_queue"]) == {"I1", "I2", "I3", "I4"}
    assert set(m["final_queues"]) == {"I1", "I2", "I3", "I4"}
    assert m["emergency_vehicle_results"][0]["completed"] is True
    _no_nonfinite(r)


def test_simulate_is_deterministic_per_seed():
    body = {"scenario": "scenario_a_balanced", "seed": 5}
    assert client.post("/api/simulate", json=body).json() == client.post("/api/simulate", json=body).json()


def test_simulate_rejects_invalid_plans_and_params():
    bad_plan = {"scenario": "scenario_a_balanced", "plan": {"I1": 30, "I2": 31, "I3": 30, "I4": 30}}
    assert client.post("/api/simulate", json=bad_plan).status_code == 422
    assert client.post("/api/simulate", json={"scenario": "scenario_a_balanced", "plan": {"I1": 30}}).status_code == 422
    assert client.post("/api/simulate", json={"scenario": "scenario_a_balanced", "seed": -1}).status_code == 422
    assert client.post("/api/simulate", json={"scenario": "scenario_a_balanced", "duty": 2}).status_code == 422


def test_optimize_runs_the_real_arbiter_and_reports_both_simulations():
    r = client.post("/api/optimize", json={"scenario": "scenario_b_congested", "seed": 42, "qaoa_maxiter": 8}).json()
    assert r["qubo"]["variables"] == 12
    assert set(r["arbiter"]["candidates"]) == {"qaoa", "sa", "greedy"}
    assert r["best_solver"] in ("qaoa", "sa", "greedy")
    assert set(r["best_plan"]) == {"I1", "I2", "I3", "I4"}
    assert r["baseline"]["plan"] == {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
    assert r["optimized"]["plan"] == r["best_plan"]
    assert isinstance(r["verdict"], str) and r["verdict"]
    assert "simulator" in r["qaoa"]["backend"].lower()
    _no_nonfinite(r)


def test_optimize_input_limits():
    assert client.post("/api/optimize", json={"scenario": "scenario_a_balanced", "qaoa_maxiter": 1000}).status_code == 422


def test_emergency_endpoint_two_ambulances_with_conflict_arbiter():
    r = client.post("/api/emergency", json={"scenario": "scenario_e_two_emergency_conflict", "seed": 42}).json()
    with_c = {v["vehicle_id"]: v for v in r["with_corridor"]["emergency_vehicle_results"]}
    without = {v["vehicle_id"]: v for v in r["without_corridor"]["emergency_vehicle_results"]}
    assert set(with_c) == {"AMB_EAST", "AMB_WEST"}
    for vid in with_c:
        assert with_c[vid]["response_time"] < without[vid]["response_time"]
    assert r["conflict_arbiter"]["num_qubits"] == 4
    assert set(r["conflict_arbiter"]["records"]) == {"qaoa", "sa", "greedy"}
    assert r["contested_junctions"]


def test_emergency_endpoint_requires_an_ambulance():
    assert client.post("/api/emergency", json={"scenario": "scenario_a_balanced"}).status_code == 422


def test_pareto_endpoint_moves_delay_between_arterial_and_cross_street():
    r = client.get("/api/pareto", params={"scenario": "scenario_d_single_emergency", "cross": 0.5}).json()
    pts = r["points"]
    assert pts[0]["lambda_param"] == 0.0 and pts[-1]["lambda_param"] == 1.0
    assert pts[-1]["mean_emergency_response_time"] < pts[0]["mean_emergency_response_time"]
    assert pts[-1]["cross_street_person_delay"] > pts[0]["cross_street_person_delay"]
    assert client.get("/api/pareto", params={"scenario": "scenario_a_balanced"}).status_code == 422


def test_noise_endpoint_is_simulation_only():
    r = client.post("/api/noise", json={"scenario": "scenario_e_two_emergency_conflict", "shots": 512}).json()
    assert set(r["runs"]) == {"ideal", "noisy"}
    assert r["hardware_requested"] is False
    assert "no quantum advantage" in r["honesty_note"]
    # a client cannot switch hardware on: unknown fields are ignored and never reach IBM
    r2 = client.post("/api/noise", json={"scenario": "scenario_e_two_emergency_conflict", "shots": 512, "use_hardware": True}).json()
    assert r2["hardware_requested"] is False and "hardware" not in r2["runs"]


def test_adaptive_endpoint_returns_replan_timeline():
    r = client.post("/api/adaptive", json={"scenario": "scenario_a_balanced", "interval": 60, "qaoa_maxiter": 5}).json()
    assert r["replan_count"] >= 1
    assert r["events"][0]["simulation_time"] == 0
    assert "jain_fairness_index" in r["adaptive"] and "total_person_delay" in r["static"]
    _no_nonfinite(r)


def test_responses_are_strict_json():
    r = client.post("/api/optimize", json={"scenario": "scenario_a_balanced", "qaoa_maxiter": 8})
    json.loads(r.text, parse_constant=lambda c: pytest.fail(f"non-standard JSON constant {c}"))
