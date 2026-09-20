"""QuantumFlow HTTP API - exposes the real backend modules to the React control center.

Run:
    python -m uvicorn api_server:app --host 127.0.0.1 --port 8000

Every endpoint calls the same simulation / QUBO / solver modules the tests and Streamlit dashboard use;
nothing here fabricates data. All QAOA runs use the local Qiskit Aer simulator. Real IBM hardware is
deliberately NOT reachable through this API (an HTTP client must never be able to spend IBM quota).

If ``dist/`` (the built React app) exists it is served at ``/`` so one process serves UI + API.
"""

import math
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from optimization.emergency_conflict import arbitrate_conflict, requests_from_configs
from optimization.ibm_hardware import compare_simulator_vs_hardware
from optimization.pareto import sweep_pareto_frontier
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.solver_arbiter import arbitrate_solvers, describe_arbiter_outcome
from simulation import belagavi
from simulation.engine import TrafficSimulator
from simulation.integration import run_adaptive_vs_static_comparison
from simulation.registry import CANONICAL_TITLES, all_scenarios, is_belagavi_inspired
from simulation.scenario import SimulationScenario

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
FIXED_PLAN = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
QUEUE_REFERENCE_VEHICLES = 40  # UI scale only: queue load % = queue / 40 (assumed, not measured)

app = FastAPI(title="QuantumFlow API", version="1.0")

_cache: Dict[Tuple, Any] = {}
_cache_lock = threading.Lock()


# --------------------------------------------------------------------------- helpers
def clean(obj: Any) -> Any:
    """Make any result JSON-safe (numpy scalars -> python, NaN/inf -> null)."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def cached(key: Tuple, fn):
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    value = clean(fn())
    with _cache_lock:
        _cache[key] = value
    return value


def get_scenario(scenario_id: str) -> SimulationScenario:
    scenarios = all_scenarios()
    if scenario_id not in scenarios:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_id}'.")
    return scenarios[scenario_id]


def node_label(scenario_id: str, node: str) -> str:
    return belagavi.junction_name(node) if is_belagavi_inspired(scenario_id) else f"Junction {node}"


def map_geo(scenario_id: str, ids: List[str]) -> Dict[str, Any]:
    """Map data for the Leaflet view: REAL OpenStreetMap locations and OSRM road geometry for Belagavi.

    The simulator nodes I1..I4 are mapped onto four real places for display. Canonical scenarios are not
    about Belagavi; they are drawn on the same corridor for display only.
    """
    geo = belagavi.load_geo()
    places = geo["junctions"]
    points = [
        {"id": n, "lat": places[i]["lat"], "lon": places[i]["lon"], "place": places[i]["name"], "osm": places[i]["osm"]}
        for i, n in enumerate(ids[: len(places)])
    ]
    legs = [
        {"from": leg["from"], "to": leg["to"], "distance_m": leg["distance_m"], "geometry": leg["geometry"]}
        for leg in geo["legs"]
    ]
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    if is_belagavi_inspired(scenario_id):
        note = (
            "Junction locations and road geometry are real (OpenStreetMap). Which junctions form the corridor, the signal timings "
            "and all traffic volumes are assumed; this is not a digital twin of Belagavi. 'Tilakwadi' is the suburb centroid."
        )
    else:
        note = (
            "Canonical scenario drawn on a real Belagavi corridor for display only: it does not model Belagavi. "
            "Locations and road geometry are real (OpenStreetMap); traffic is simulated."
        )
    return {
        "kind": "openstreetmap",
        "centre": {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons)},
        "points": points,
        "legs": legs,
        "attribution": geo["attribution"],
        "retrieved": geo["retrieved"],
        "note": note,
    }


def traffic_state(sc: SimulationScenario) -> Dict[str, Dict[str, float]]:
    return {i: {"queue": float(sc.initial_queues.get(i, 10)), "density": 0.3} for i in sc.intersections}


def slim_metrics(m: Dict[str, Any]) -> Dict[str, Any]:
    """Simulation metrics without the (long) corridor event log."""
    out = {k: v for k, v in m.items() if k != "corridor_event_log"}
    out["corridor_event_log"] = [
        {"timestamp": e["timestamp"], "event_type": e["event_type"], "message": e["message"]}
        for e in m.get("corridor_event_log", [])[:80]
    ]
    return out


def simulate(sc: SimulationScenario, plan: Dict[str, int], seed: int, corridor: bool, duty: float = 1.0) -> Dict[str, Any]:
    sim = TrafficSimulator(sc, enable_emergency_corridor=corridor, preemption_duty=duty)
    return slim_metrics(sim.simulate(signal_plan=dict(plan), seed=seed).to_dict())


def validate_plan(sc: SimulationScenario, plan: Optional[Dict[str, int]]) -> Dict[str, int]:
    if plan is None:
        return dict(FIXED_PLAN)
    try:
        sc.validate_plan(plan)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {k: int(v) for k, v in plan.items()}


# --------------------------------------------------------------------------- request models
class SimulateRequest(BaseModel):
    scenario: str
    seed: int = Field(42, ge=0, le=10_000)
    plan: Optional[Dict[str, int]] = None
    corridor: bool = False
    duty: float = Field(1.0, ge=0.0, le=1.0)


class OptimizeRequest(BaseModel):
    scenario: str
    seed: int = Field(42, ge=0, le=10_000)
    qaoa_maxiter: int = Field(30, ge=5, le=60)


class AdaptiveRequest(BaseModel):
    scenario: str
    seed: int = Field(42, ge=0, le=10_000)
    interval: int = Field(60, ge=30, le=120)
    qaoa_maxiter: int = Field(15, ge=5, le=40)


class EmergencyRequest(BaseModel):
    scenario: str
    seed: int = Field(42, ge=0, le=10_000)
    plan: Optional[Dict[str, int]] = None


class NoiseRequest(BaseModel):
    scenario: str
    seed: int = Field(42, ge=0, le=10_000)
    junction: Optional[str] = None
    shots: int = Field(2048, ge=256, le=8192)


# --------------------------------------------------------------------------- endpoints
@app.get("/api/health")
def health() -> Dict[str, Any]:
    import qiskit
    import qiskit_aer

    return {
        "status": "online",
        "quantum_backend": "Qiskit Aer (local classical simulator)",
        "real_hardware_reachable_via_api": False,
        "qiskit": qiskit.__version__,
        "qiskit_aer": qiskit_aer.__version__,
    }


@app.get("/api/scenarios")
def scenarios() -> List[Dict[str, Any]]:
    out = []
    for sid, sc in all_scenarios().items():
        out.append(
            {
                "id": sid,
                "title": CANONICAL_TITLES.get(sid, sid),
                "belagavi_inspired": is_belagavi_inspired(sid),
                "ambulances": len(sc.get_all_emergency_configs()),
                "has_cross_street_traffic": bool(sc.cross_street_rates),
                "duration_seconds": sc.duration_seconds,
            }
        )
    return out


@app.get("/api/network")
def network(scenario: str) -> Dict[str, Any]:
    sc = get_scenario(scenario)
    ids = list(sc.intersections)
    nodes = [
        {
            "id": n,
            "name": node_label(scenario, n),
            "initial_queue": int(sc.initial_queues.get(n, 0)),
            "arrival_rate": float(sc.arrival_rates.get(n, 0.0)),
            "bus_probability": float(sc.bus_probabilities.get(n, 0.0)),
            "cross_street_rate": float(sc.cross_street_rates.get(n, 0.0)),
        }
        for n in ids
    ]
    edges = [{"id": f"R{i + 1}", "from": ids[i], "to": ids[i + 1]} for i in range(len(ids) - 1)]
    ambulances = [
        {"vehicle_id": c.vehicle_id, "priority": c.priority, "route": list(c.route), "arrival_time": c.arrival_time}
        for c in sc.get_all_emergency_configs()
    ]
    return {
        "scenario_id": scenario,
        "title": CANONICAL_TITLES.get(scenario, scenario),
        "belagavi_inspired": is_belagavi_inspired(scenario),
        "disclaimer": belagavi.DISCLAIMER if is_belagavi_inspired(scenario) else None,
        "nodes": nodes,
        "edges": edges,
        "ambulances": ambulances,
        "cycle_length": sc.cycle_length,
        "duration_seconds": sc.duration_seconds,
        "geo": map_geo(scenario, ids),
        "fixed_plan": dict(FIXED_PLAN),
        "queue_reference_vehicles": QUEUE_REFERENCE_VEHICLES,
        "occupancy": {
            "car": sc.vehicle_type_config.car_occupancy,
            "bus": sc.vehicle_type_config.bus_occupancy,
        },
    }


@app.get("/api/graph")
def graph(scenario: str) -> Dict[str, Any]:
    """Graph analytics computed with NetworkX on the scenario's junction graph."""
    sc = get_scenario(scenario)
    ids = list(sc.intersections)
    hop = sc.travel_time_between_intersections

    def run() -> Dict[str, Any]:
        G = nx.Graph()
        for n in ids:
            G.add_node(n, label=node_label(scenario, n))
        for i in range(len(ids) - 1):
            G.add_edge(ids[i], ids[i + 1], travel_time_s=hop)
        deg = dict(G.degree())
        bet = nx.betweenness_centrality(G, normalized=True)
        clo = nx.closeness_centrality(G)
        cut = set(nx.articulation_points(G))
        connected = nx.is_connected(G)
        paths = []
        for c in sc.get_all_emergency_configs():
            sp = nx.shortest_path(G, c.route[0], c.route[-1], weight="travel_time_s")
            paths.append(
                {
                    "vehicle_id": c.vehicle_id,
                    "route": list(c.route),
                    "shortest_path": sp,
                    "route_is_shortest": list(c.route) == sp,
                    "travel_time_s": nx.shortest_path_length(G, c.route[0], c.route[-1], weight="travel_time_s"),
                }
            )
        return {
            "library": f"networkx {nx.__version__}",
            "graph": {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "connected": connected,
                "diameter_hops": nx.diameter(G) if connected else None,
                "density": nx.density(G),
                "is_path_graph": all(d <= 2 for d in deg.values()) and G.number_of_edges() == G.number_of_nodes() - 1,
            },
            "nodes": [
                {
                    "id": n,
                    "name": node_label(scenario, n),
                    "degree": deg[n],
                    "betweenness": bet[n],
                    "closeness": clo[n],
                    "is_articulation_point": n in cut,
                }
                for n in ids
            ],
            "edges": [{"from": u, "to": v, "travel_time_s": d["travel_time_s"]} for u, v, d in G.edges(data=True)],
            "ambulance_paths": paths,
            "note": "The arterial is a path graph, so centrality is determined purely by position; travel time is the simulator's per-hop parameter.",
        }

    return JSONResponse(cached(("graph", scenario), run))


@app.post("/api/simulate")
def simulate_endpoint(req: SimulateRequest) -> JSONResponse:
    sc = get_scenario(req.scenario)
    plan = validate_plan(sc, req.plan)
    key = ("sim", req.scenario, req.seed, tuple(sorted(plan.items())), req.corridor, round(req.duty, 3))
    data = cached(key, lambda: {"plan": plan, "metrics": simulate(sc, plan, req.seed, req.corridor, req.duty)})
    return JSONResponse(data)


@app.post("/api/optimize")
def optimize(req: OptimizeRequest) -> JSONResponse:
    sc = get_scenario(req.scenario)

    def run() -> Dict[str, Any]:
        cfg = FullQUBOConfig()
        qubo = build_qubo(traffic_state(sc), None, config=cfg)
        res = arbitrate_solvers(qubo, qaoa_maxiter=req.qaoa_maxiter, seed=req.seed)
        best_plan = dict(res.best_plan)
        baseline = simulate(sc, FIXED_PLAN, req.seed, False)
        optimized = simulate(sc, best_plan, req.seed, False)
        arb = res.to_dict()
        return {
            "qubo": {
                "variables": qubo.num_variables,
                "qubits": qubo.num_variables,
                "terms": ["waiting", "capacity pressure", "throughput", "inter-junction coupling", "one-hot constraint"],
                "weights": {
                    "onehot_penalty": cfg.onehot_penalty,
                    "wait_weight": cfg.wait_weight,
                    "capacity_weight": cfg.capacity_weight,
                    "throughput_weight": cfg.throughput_weight,
                    "coupling_weight": cfg.coupling_weight,
                },
            },
            "qaoa": {"p": 1, "shots": 1024, "maxiter": req.qaoa_maxiter, "backend": "Qiskit Aer simulator"},
            "arbiter": arb,
            "verdict": describe_arbiter_outcome(res),
            "best_solver": res.best_solver,
            "best_plan": best_plan,
            "best_energy": res.best_energy,
            "baseline": {"plan": dict(FIXED_PLAN), "metrics": baseline},
            "optimized": {"plan": best_plan, "metrics": optimized},
            "note": "QUBO energy measures the optimisation objective, not simulated traffic outcomes; compare the two simulated runs for the latter.",
        }

    return JSONResponse(cached(("opt", req.scenario, req.seed, req.qaoa_maxiter), run))


@app.post("/api/adaptive")
def adaptive(req: AdaptiveRequest) -> JSONResponse:
    sc = get_scenario(req.scenario)

    def run() -> Dict[str, Any]:
        res = run_adaptive_vs_static_comparison(
            scenario=sc, seed=req.seed, replan_interval=req.interval, qaoa_maxiter=req.qaoa_maxiter
        )
        keep = [
            "average_waiting_time", "max_approach_wait", "jain_fairness_index", "total_person_delay",
            "average_person_delay", "throughput", "starvation_violations", "estimated_co2_kg",
            "max_queue", "normal_signal_plan",
        ]
        return {
            "static": {k: res["static"][k] for k in keep},
            "adaptive": {k: res["adaptive"][k] for k in keep},
            "events": res["adaptive"]["replanning_events"],
            "replan_count": res["adaptive"]["replan_count"],
            "qaoa_executions": res["adaptive"]["qaoa_execution_count"],
            "sa_fallbacks": res["adaptive"]["sa_fallback_count"],
            "interval": req.interval,
        }

    return JSONResponse(cached(("adaptive", req.scenario, req.seed, req.interval, req.qaoa_maxiter), run))


@app.post("/api/emergency")
def emergency(req: EmergencyRequest) -> JSONResponse:
    sc = get_scenario(req.scenario)
    plan = validate_plan(sc, req.plan)
    if not sc.get_all_emergency_configs():
        raise HTTPException(status_code=422, detail="This scenario has no emergency vehicles.")

    def run() -> Dict[str, Any]:
        without = simulate(sc, plan, req.seed, False)
        with_c = simulate(sc, plan, req.seed, True)
        contested = sorted(
            {i for c in sc.get_all_emergency_configs() for i in c.route
             if sum(i in d.route for d in sc.get_all_emergency_configs()) >= 2}
        )
        conflict = None
        if contested:
            junction = contested[0]
            reqs = requests_from_configs(sc.get_all_emergency_configs(), junction)
            if 2 <= len(reqs) <= 4:
                conflict = arbitrate_conflict(reqs, junction, seed=req.seed).to_dict()
        return {
            "plan": plan,
            "without_corridor": without,
            "with_corridor": with_c,
            "conflict_arbiter": conflict,
            "contested_junctions": contested,
        }

    return JSONResponse(cached(("emg", req.scenario, req.seed, tuple(sorted(plan.items()))), run))


@app.get("/api/pareto")
def pareto(scenario: str, seed: int = Query(42, ge=0, le=10_000), cross: float = Query(0.5, ge=0.0, le=0.8)) -> JSONResponse:
    sc = get_scenario(scenario)
    if not sc.get_all_emergency_configs():
        raise HTTPException(status_code=422, detail="Pareto analysis needs a scenario with an emergency vehicle.")
    return JSONResponse(
        cached(
            ("pareto", scenario, seed, round(cross, 3)),
            lambda: sweep_pareto_frontier(sc, seed=seed, cross_street_rate=cross).to_dict(),
        )
    )


@app.post("/api/noise")
def noise(req: NoiseRequest) -> JSONResponse:
    """Ideal vs noisy SIMULATION only. Real hardware is intentionally not exposed over HTTP."""
    sc = get_scenario(req.scenario)
    configs = sc.get_all_emergency_configs()
    counts: Dict[str, int] = {}
    for c in configs:
        for i in c.route:
            counts[i] = counts.get(i, 0) + 1
    contested = [i for i, n in counts.items() if n >= 2]
    if not contested:
        raise HTTPException(status_code=422, detail="Needs a scenario with two ambulances sharing a junction.")
    junction = req.junction if req.junction in contested else contested[0]
    reqs = requests_from_configs(configs, junction)[:3]
    return JSONResponse(
        cached(
            ("noise", req.scenario, req.seed, junction, req.shots),
            lambda: compare_simulator_vs_hardware(reqs, junction, shots=req.shots, seed=req.seed, use_hardware=False).to_dict(),
        )
    )


# --------------------------------------------------------------------------- static UI (optional)
if os.path.isfile(os.path.join(DIST, "index.html")):
    if os.path.isdir(os.path.join(DIST, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = os.path.normpath(os.path.join(DIST, full_path))
        if full_path and candidate.startswith(DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(DIST, "index.html"))
