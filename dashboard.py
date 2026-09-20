"""QuantumFlow live dashboard (Streamlit).

Tabs: adaptive control, people & fairness, ambulances (conflict QUBO + arbiter), solver arbiter,
Pareto slider, ideal-vs-noisy simulator comparison (real IBM hardware is opt-in and unverified),
Belagavi-inspired corridor (real OpenStreetMap locations, assumed traffic).

Every number shown is computed from a simulation or solver run in this session; nothing is
hard-coded. All QAOA runs use the local Qiskit Aer simulator unless the user explicitly opts in to real hardware.
"""

import dataclasses
import importlib.util
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

from optimization.emergency_conflict import arbitrate_conflict, requests_from_configs
from optimization.ibm_hardware import compare_simulator_vs_hardware
from optimization.pareto import sweep_pareto_frontier
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.solver_arbiter import arbitrate_solvers, describe_arbiter_outcome
from simulation import belagavi
from simulation.engine import TrafficSimulator
from simulation.integration import run_adaptive_vs_static_comparison
from simulation.registry import all_scenarios
from simulation.scenario import SimulationScenario

DEFAULT_PLAN = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}


# --------------------------------------------------------------------------- helpers
def _label(node: str, use_names: bool) -> str:
    return f"{belagavi.junction_name(node)} ({node})" if use_names else node


def _plan_frame(plan: Dict[str, int], use_names: bool) -> pd.DataFrame:
    return pd.DataFrame({"Junction": [_label(k, use_names) for k in plan], "Green (s)": list(plan.values())})


def _traffic_state(sc: SimulationScenario) -> Dict[str, Dict[str, float]]:
    return {i: {"queue": float(sc.initial_queues.get(i, 10)), "density": 0.3} for i in sc.intersections}


@st.cache_data(show_spinner=False)
def _adaptive_vs_static(key: str, seed: int, interval: int, maxiter: int) -> Dict[str, Any]:
    return run_adaptive_vs_static_comparison(
        scenario=all_scenarios()[key], seed=seed, replan_interval=interval, qaoa_maxiter=maxiter
    )


@st.cache_data(show_spinner=False)
def _ambulance_runs(key: str, seed: int) -> Dict[str, Any]:
    sc = all_scenarios()[key]
    out = {}
    for name, corridor in (("without corridor", False), ("with corridor", True)):
        m = TrafficSimulator(sc, enable_emergency_corridor=corridor).simulate(dict(DEFAULT_PLAN), seed=seed)
        out[name] = m.to_dict()
    return out


@st.cache_data(show_spinner=False)
def _arbiter_run(key: str, seed: int, maxiter: int) -> Dict[str, Any]:
    sc = all_scenarios()[key]
    qubo = build_qubo(_traffic_state(sc), None, config=FullQUBOConfig())
    res = arbitrate_solvers(qubo, qaoa_maxiter=maxiter, seed=seed)
    return {"result": res.to_dict(), "verdict": describe_arbiter_outcome(res)}


@st.cache_data(show_spinner=False)
def _pareto_run(key: str, seed: int, cross: float, lambdas: tuple) -> Dict[str, Any]:
    sc = all_scenarios()[key]
    return sweep_pareto_frontier(sc, lambda_values=lambdas, seed=seed, cross_street_rate=cross).to_dict()


@st.cache_data(show_spinner=False)
def _conflict_arbiter(key: str, seed: int, junction: str) -> Dict[str, Any]:
    sc = all_scenarios()[key]
    reqs = requests_from_configs(sc.get_all_emergency_configs(), junction)
    return arbitrate_conflict(reqs, junction, seed=seed).to_dict()


@st.cache_data(show_spinner=False)
def _hardware_run(key: str, seed: int, junction: str, shots: int, use_hw: bool) -> Dict[str, Any]:
    sc = all_scenarios()[key]
    reqs = requests_from_configs(sc.get_all_emergency_configs(), junction)[:3]
    return compare_simulator_vs_hardware(reqs, junction, shots=shots, seed=seed, use_hardware=use_hw).to_dict()


def _contested_junctions(sc: SimulationScenario) -> List[str]:
    counts: Dict[str, int] = {}
    for cfg in sc.get_all_emergency_configs():
        for inter in cfg.route:
            counts[inter] = counts.get(inter, 0) + 1
    return [i for i, c in counts.items() if c >= 2]


# --------------------------------------------------------------------------- tabs
def _tab_adaptive(sc: SimulationScenario, seed: int, use_names: bool) -> None:
    st.subheader("Adaptive rolling-horizon optimisation")
    st.caption("Traffic is re-read every N seconds and the QUBO is solved again; the plan is never computed just once.")
    c1, c2 = st.columns(2)
    interval = c1.select_slider("Re-optimise every (s)", options=[30, 60, 90, 120], value=60)
    maxiter = c2.slider("QAOA iterations per solve", 5, 40, 15)
    if not st.button("Run static vs adaptive", key="run_adaptive"):
        st.info("Press the button to run both controllers on identical traffic (QAOA on Aer, SA fallback).")
        return
    with st.spinner("Solving and simulating..."):
        res = _adaptive_vs_static(sc.scenario_id, seed, interval, maxiter)
    st.session_state["last_run"] = res
    _show_adaptive(res, use_names)


def _show_adaptive(res: Dict[str, Any], use_names: bool) -> None:
    s, a = res["static"], res["adaptive"]
    st.markdown(f"**Replans:** {a['replan_count']} scheduled · QAOA solves: {a['qaoa_execution_count']} · SA fallbacks: {a['sa_fallback_count']}")
    events = a["replanning_events"]
    if events:
        rows = [
            {
                "t (s)": e["simulation_time"],
                "solver": e["solver_used"],
                "energy": round(e["optimization_energy"], 2),
                "queues": ", ".join(f"{k}:{int(v)}" for k, v in e["queue_state"].items()),
                **{f"{k} green": v for k, v in e["signal_plan"].items()},
            }
            for e in events
        ]
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
        long = df.melt(id_vars=["t (s)"], value_vars=[c for c in df.columns if c.endswith("green")], var_name="Junction", value_name="Green (s)")
        st.altair_chart(
            alt.Chart(long).mark_line(point=True).encode(
                x=alt.X("t (s):Q"), y=alt.Y("Green (s):Q", scale=alt.Scale(domain=[10, 50])), color="Junction:N"
            ).properties(height=220),
            width="stretch",
        )
    _kpi_compare(s, a)


def _kpi_compare(s: Dict[str, Any], a: Dict[str, Any]) -> None:
    def row(label: str, key: str, fmt: str = "{:,.1f}") -> Dict[str, str]:
        return {"Metric": label, "Static": fmt.format(s[key]), "Adaptive": fmt.format(a[key])}

    st.dataframe(
        pd.DataFrame(
            [
                row("Average wait (s / vehicle)", "average_waiting_time"),
                row("Max approach wait (s)", "max_approach_wait"),
                row("Jain fairness index (1.0 = equal)", "jain_fairness_index", "{:.3f}"),
                row("Total person-delay (person-s)", "total_person_delay", "{:,.0f}"),
                row("Avg person-delay (s / person)", "average_person_delay"),
                row("Throughput (vehicles)", "throughput", "{:,.0f}"),
                row("Starvation violations (>120 s)", "starvation_violations", "{:,.0f}"),
                row("Est. CO2 (kg)", "estimated_co2_kg", "{:.2f}"),
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption("Lower is better except fairness and throughput. Differences on one seed are indicative, not statistically established.")


def _tab_people(sc: SimulationScenario, seed: int) -> None:
    st.subheader("People, not just vehicles")
    st.caption("Cars carry the scenario's occupancy, buses carry ~30-40 people; the objective and metrics count person-delay.")
    cfg = sc.vehicle_type_config
    c1, c2, c3 = st.columns(3)
    c1.metric("Car occupancy", f"{cfg.car_occupancy:g}")
    c2.metric("Bus occupancy", f"{cfg.bus_occupancy:g}")
    c3.metric("Bus share (entry nodes)", ", ".join(f"{k}:{v:.0%}" for k, v in sc.bus_probabilities.items()) or "none")
    run = st.session_state.get("last_run")
    if run is None:
        st.info("Run the Adaptive tab first to see person-delay and fairness for this scenario.")
        return
    a = run["adaptive"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Average wait", f"{a['average_waiting_time']:.1f} s")
    m2.metric("Maximum wait", f"{a['max_approach_wait']:.0f} s")
    m3.metric("Jain fairness", f"{a['jain_fairness_index']:.2f}")
    m4.metric("Person-delay", f"{a['total_person_delay']:,.0f} p·s")
    st.caption(f"Scenario shown in the last run: {a['scenario_id']}.")


def _tab_ambulances(sc: SimulationScenario, seed: int, use_names: bool) -> None:
    st.subheader("Emergency vehicles")
    cfgs = sc.get_all_emergency_configs()
    if not cfgs:
        st.info("This scenario has no ambulances. Pick scenario D, E, F or the Belagavi two-ambulance scenario.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Vehicle": c.vehicle_id,
                    "Priority": c.priority,
                    "Spawns (s)": c.arrival_time,
                    "Route": " → ".join(_label(n, use_names) for n in c.route),
                }
                for c in cfgs
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    runs = _ambulance_runs(sc.scenario_id, seed)
    rows = []
    for mode, m in runs.items():
        for r in m["emergency_vehicle_results"]:
            rows.append({"Mode": mode, "Vehicle": r["vehicle_id"], "Response (s)": r["response_time"], "Waited (s)": r["waiting_time"]})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    with_c = runs["with corridor"]
    log = [e["message"] for e in with_c["corridor_event_log"] if "Conflict" in e["message"]]
    st.markdown(f"**Conflicts resolved by the conflict-QUBO:** {with_c['resolved_emergency_conflicts']}")
    for msg in log:
        st.write("•", msg)

    contested = _contested_junctions(sc)
    if not contested:
        st.info("Only one ambulance uses each junction here, so there is no conflict to arbitrate.")
        return
    junction = st.selectbox("Contested junction", contested, format_func=lambda n: _label(n, use_names))
    if st.button("Arbitrate conflict: QAOA vs SA vs Greedy", key="arb_conflict"):
        with st.spinner("Solving the same small QUBO three ways..."):
            res = _conflict_arbiter(sc.scenario_id, seed, junction)
        st.markdown(f"**{res['num_qubits']}-qubit conflict QUBO** · exact optimum energy {res['exact_energy']:.2f}")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Solver": r["solver_name"],
                        "Order": " → ".join(r["sequence"]) or "invalid",
                        "Energy": round(r["energy"], 3),
                        "Optimal": r["is_optimal"],
                        "Runtime (s)": round(r["runtime_seconds"], 4),
                        "Note": r["note"],
                    }
                    for r in res["records"].values()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.success(res["verdict"])


def _tab_arbiter(sc: SimulationScenario, seed: int) -> None:
    st.subheader("Solver arbiter: same QUBO, three solvers")
    maxiter = st.slider("QAOA iterations", 5, 60, 30, key="arb_iter")
    if not st.button("Run arbiter on this scenario's traffic state", key="run_arbiter"):
        return
    with st.spinner("Running QAOA, SA and Greedy on the identical 12-variable QUBO..."):
        out = _arbiter_run(sc.scenario_id, seed, maxiter)
    res = out["result"]
    df = pd.DataFrame(
        [
            {
                "Solver": k,
                "Energy": round(r["qubo_energy"], 3),
                "Runtime (s)": round(r["runtime_seconds"], 4),
                "Feasible": r["is_feasible"],
                "Plan": ", ".join(f"{i}:{d}" for i, d in r["signal_plan"].items()),
            }
            for k, r in res["candidates"].items()
        ]
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(x="Solver:N", y=alt.Y("Energy:Q", title="QUBO energy (lower is better)"), color="Solver:N").properties(height=220),
        width="stretch",
    )
    st.info(out["verdict"])


def _tab_pareto(sc: SimulationScenario, seed: int) -> None:
    st.subheader("Pareto trade-off: ambulance speed vs civilian delay")
    if not sc.get_all_emergency_configs():
        st.info("Pick a scenario with at least one ambulance (D, E, F or Belagavi two-ambulance).")
        return
    cross = st.slider(
        "Cross-street demand (vehicles/s per junction)", 0.0, 0.8, 0.5, 0.05,
        help="Preemption takes green from cross streets. With little cross traffic it costs civilians almost nothing.",
    )
    lambdas = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    with st.spinner("Sweeping emergency priority..."):
        fr = _pareto_run(sc.scenario_id, seed, cross, lambdas)
    pts = pd.DataFrame(fr["points"])
    pts = pts.dropna(subset=["mean_emergency_response_time"])
    if pts.empty:
        st.warning("No ambulance finished its route in any run.")
        return
    xmode = st.radio(
        "Cost axis",
        ["Cross-street delay (who pays for preemption)", "Total civilian delay"],
        horizontal=True,
    )
    xcol = "cross_street_person_delay" if xmode.startswith("Cross") else "person_delay"
    xtitle = "Cross-street person-delay (person-s)" if xcol == "cross_street_person_delay" else "Total civilian person-delay (person-s)"
    lam = st.select_slider("Emergency priority λ (0 = civilians only, 1 = full preemption)", options=list(pts["lambda_param"]), value=float(pts["lambda_param"].iloc[-1]))
    pts["selected"] = pts["lambda_param"] == lam
    chart = (
        alt.Chart(pts).mark_line(color="#888").encode(x=alt.X(f"{xcol}:Q", title=xtitle, scale=alt.Scale(zero=False)),
                                                        y=alt.Y("mean_emergency_response_time:Q", title="Mean ambulance response (s)", scale=alt.Scale(zero=False)), order="lambda_param:Q")
        + alt.Chart(pts).mark_circle(size=140).encode(
            x=f"{xcol}:Q", y="mean_emergency_response_time:Q",
            color=alt.condition("datum.selected", alt.value("#d62728"), alt.value("#1f77b4")),
            tooltip=["lambda_param", "mean_emergency_response_time", "person_delay", "arterial_person_delay", "cross_street_person_delay"],
        )
    ).properties(height=320)
    st.altair_chart(chart, width="stretch")
    sel = pts[pts["lambda_param"] == lam].iloc[0]
    base = pts.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ambulance response", f"{sel['mean_emergency_response_time']:.0f} s", f"{sel['mean_emergency_response_time'] - base['mean_emergency_response_time']:+.0f} s vs λ=0", delta_color="inverse")
    c2.metric("Civilian person-delay", f"{sel['person_delay']:,.0f}", f"{sel['person_delay'] - base['person_delay']:+,.0f} vs λ=0", delta_color="inverse")
    c3.metric("Cross-street delay", f"{sel['cross_street_person_delay']:,.0f}", f"{sel['cross_street_person_delay'] - base['cross_street_person_delay']:+,.0f} vs λ=0", delta_color="inverse")
    c4.metric("Fairness (Jain)", f"{sel['jain_fairness_index']:.2f}")
    st.caption(
        f"Arterial delay {sel['arterial_person_delay']:,.0f} + cross-street delay {sel['cross_street_person_delay']:,.0f}. "
        "lambda also changes the QUBO emergency weight, so the chosen signal plan can vary with lambda; arterial, cross-street and total delay depend on the scenario and cross-street demand (try the slider above). "
        "This is a modelling result on a toy network, not a recommendation for a real junction."
    )
    with st.expander("All points"):
        st.dataframe(pts.drop(columns=["signal_plan", "selected"]), width="stretch", hide_index=True)


def _tab_hardware(sc: SimulationScenario, seed: int, use_names: bool) -> None:
    st.subheader("Ideal vs noisy simulation (real hardware: optional, unverified)")
    st.caption(
        "Same conflict-QUBO circuit and QAOA angles, sampled on ideal Aer and a generic noisy Aer model. "
        "Real IBM hardware execution is an optional future validation: the runtime path is implemented but has not been verified against an actual device."
    )
    contested = _contested_junctions(sc)
    if not contested:
        st.info("Pick a scenario with two conflicting ambulances (E, F or Belagavi two-ambulance).")
        return
    junction = st.selectbox("Junction", contested, key="hw_j", format_func=lambda n: _label(n, use_names))
    shots = st.select_slider("Shots", options=[512, 1024, 2048, 4096], value=2048)
    have_runtime = importlib.util.find_spec("qiskit_ibm_runtime") is not None
    use_hw = False
    if have_runtime:
        use_hw = st.checkbox(
            "Also submit this circuit to a real IBM quantum computer (uses your IBM quota, sends the circuit to IBM)",
            value=False,
        )
    else:
        st.caption("Real-hardware option hidden: `qiskit-ibm-runtime` is not installed (`pip install -r requirements-ibm.txt`).")
    if not st.button("Run comparison", key="run_hw"):
        return
    with st.spinner("Tuning QAOA and sampling..."):
        res = _hardware_run(sc.scenario_id, seed, junction, shots, use_hw)
    st.markdown(f"**{res['num_qubits']} qubits** · transpiled depth {res['circuit_depth_transpiled']} · {res['two_qubit_gate_count']} CX · exact optimum {' → '.join(res['exact_sequence'])} (energy {res['exact_energy']:.2f})")
    df = pd.DataFrame(
        [
            {
                "Backend": r["backend_name"],
                "Valid orderings": f"{r['valid_fraction']:.1%}",
                "Hit optimum": f"{r['optimal_probability']:.1%}",
                "Mean energy": round(r["expected_energy"], 2),
                "Distance from ideal (TVD)": round(r["tvd_vs_ideal"], 3),
            }
            for r in res["runs"].values()
        ]
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.write("Hardware:", res["hardware_status"])
    st.info(res["honesty_note"])


def _tab_twin(sc: SimulationScenario) -> None:
    st.subheader("Belagavi-inspired corridor (real OpenStreetMap locations, assumed traffic)")
    info = belagavi.describe()
    st.warning(info["disclaimer"])
    df = pd.DataFrame(info["junctions"])[["node_id", "name", "lat", "lon", "osm", "role"]]
    st.dataframe(df.rename(columns={"node_id": "Node", "name": "Place (OpenStreetMap)", "lat": "Lat", "lon": "Lon", "osm": "OSM object", "role": "Role in the story"}), width="stretch", hide_index=True)
    order = info["corridor_order"]
    pos = pd.DataFrame({"x": range(len(order)), "y": [0] * len(order), "label": [f"{belagavi.junction_name(n)}\n({n})" for n in order]})
    line = alt.Chart(pos).mark_line(color="#888").encode(x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None))
    dots = alt.Chart(pos).mark_circle(size=400).encode(x="x:Q", y="y:Q")
    text = alt.Chart(pos).mark_text(dy=-28).encode(x="x:Q", y="y:Q", text="label:N")
    st.altair_chart((line + dots + text).properties(height=140), width="stretch")
    st.caption("Schematic order only; the React control center draws the real road geometry on an OpenStreetMap map. Tilakwadi is a suburb centroid.")


# --------------------------------------------------------------------------- entry
def render_dashboard() -> None:
    st.title("🚦 QuantumFlow")
    st.caption("Adaptive, people-aware, fairness-constrained traffic control · QUBO/QAOA vs simulated annealing vs greedy · QAOA runs on the local Qiskit Aer simulator; no quantum advantage is claimed.")

    scenarios = all_scenarios()
    with st.sidebar:
        st.header("Scenario")
        key = st.selectbox("Scenario", list(scenarios), index=list(scenarios).index("scenario_e_two_emergency_conflict"))
        seed = st.number_input("Random seed", 0, 10_000, 42)
        use_names = st.toggle("Show Belagavi-inspired junction labels", value=key.startswith("belagavi"))
        st.caption("Scenarios A–G are canonical benchmarks; Belagavi-inspired ones use assumed, not measured, demand.")
        st.caption("React control center: `python -m uvicorn api_server:app --port 8000`, then open http://127.0.0.1:8000")
    sc = scenarios[key]

    tabs = st.tabs(["Adaptive", "People & fairness", "Ambulances", "Solver arbiter", "Pareto slider", "Noise & hardware", "Belagavi corridor"])
    with tabs[0]:
        _tab_adaptive(sc, int(seed), use_names)
    with tabs[1]:
        _tab_people(sc, int(seed))
    with tabs[2]:
        _tab_ambulances(sc, int(seed), use_names)
    with tabs[3]:
        _tab_arbiter(sc, int(seed))
    with tabs[4]:
        _tab_pareto(sc, int(seed))
    with tabs[5]:
        _tab_hardware(sc, int(seed), use_names)
    with tabs[6]:
        _tab_twin(sc)
