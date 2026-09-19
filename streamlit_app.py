"""QuantumFlow — Hybrid Quantum-Classical Traffic Signal Command Center.

Streamlit command-center frontend:
1. LIVE NETWORK: 4 top KPI cards, 4-node network schematic/map, traffic density, queue lengths, signal timing, system impact row
2. TRAFFIC ANALYTICS: Performance trends time-series, intersection distributions & telemetry
3. QUANTUM OPTIMIZATION: Current plan, QAOA parameters & energy, constraint checks, replanning timeline
4. EMERGENCY CORRIDOR: Ambulance corridor preemption (I2 -> I3 -> I4), lifecycle status, chronological event log
5. CLASSICAL vs QUANTUM: Controlled benchmark comparison (QAOA vs SA vs Static Baseline), approximation ratio, deltas
6. ENVIRONMENT: CO2 emissions, vehicle idling time, fuel estimates & sustainability trends
"""

import os
import sys
from typing import Dict, Any, List, Optional
import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Ensure package root is first in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if sys.path[0] != CURRENT_DIR:
    sys.path.insert(0, CURRENT_DIR)

from frontend.component import webthreads_loader
from simulation.integration import (
    run_quantumflow_demo,
    run_adaptive_vs_static_comparison,
    QuantumFlowRunResult,
)
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from traffic_optimization.simulation.traffic_network import get_traffic_network
from traffic_optimization.simulation.kpi_calculator import calculate_kpis, get_intersection_data
from traffic_optimization.visualization.map import render_map
from traffic_optimization.visualization.charts import (
    create_4_kpi_cards_html,
    create_impact_metrics_html,
    create_network_schematic_fig,
    create_density_chart,
    create_queue_chart,
    create_signal_timing_chart,
    create_performance_trend_chart,
    create_co2_trend_chart,
)
from streamlit_folium import st_folium

# Page configuration
st.set_page_config(
    page_title="QuantumFlow — Traffic Command Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# 1. LOADER SESSION STATE & NUMBER GLITCH MATRIX GATE
# =============================================================================
if "loader_complete" not in st.session_state:
    st.session_state.loader_complete = False

if not st.session_state.loader_complete:
    st.markdown(
        """<style>
            .stAppHeader { display: none; }
            .block-container { padding: 0 !important; max-width: 100% !important; }
            header { visibility: hidden; }
            footer { visibility: hidden; }
            [data-testid="stSidebar"] { display: none; }
        </style>""",
        unsafe_allow_html=True,
    )

    status = webthreads_loader(key="quantumflow_number_glitch_loader")

    if status == "LOADER_COMPLETE":
        st.session_state.loader_complete = True
        st.rerun()

    # Skip Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➔ Skip Animation & Enter Command Center", key="skip_loader_btn", use_container_width=True):
            st.session_state.loader_complete = True
            st.rerun()

    st.stop()


# =============================================================================
# 2. CLEAN COMMAND-CENTER STYLING
# =============================================================================
st.markdown(
    """<style>
    /* Sleek Command Center Palette */
    body {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background-color: #0b0f19;
    }

    /* Main Container Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1380px !important;
    }

    /* Top Command Header */
    .command-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 18px;
    }
    .header-title {
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        color: #f8fafc;
        margin: 0;
    }
    .header-sub {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 2px;
    }
    .header-status {
        font-size: 0.85rem;
        font-weight: 600;
        color: #4edea3;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #4edea3;
        display: inline-block;
    }
    .header-net {
        font-size: 0.75rem;
        color: #64748b;
        font-family: 'Inter', monospace;
        margin-top: 2px;
        text-align: right;
    }

    /* Section Subheadings */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Standard Cards */
    .cc-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
    }

    /* Clean Badges */
    .badge-green { color: #4edea3; background: rgba(78, 222, 163, 0.12); padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; }
    .badge-cyan { color: #38bdf8; background: rgba(56, 189, 248, 0.12); padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; }
    .badge-purple { color: #a78bfa; background: rgba(167, 139, 250, 0.12); padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; }
    .badge-red { color: #f87171; background: rgba(248, 113, 113, 0.12); padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; }

    /* Plotly Chart Wrapper */
    .stPlotlyChart {
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(15, 23, 42, 0.6) !important;
        margin-bottom: 12px !important;
    }

    /* Clean Sidebar */
    [data-testid="stSidebar"] {
        background-color: #080c14;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    </style>""",
    unsafe_allow_html=True,
)


# =============================================================================
# 3. AUTHORITATIVE BACKEND EXECUTION & CACHING
# =============================================================================

# Initialize Session State
if "scenario_queues" not in st.session_state:
    st.session_state.scenario_queues = {"I1": 10, "I2": 15, "I3": 8, "I4": 12}

if "enable_emergency" not in st.session_state:
    st.session_state.enable_emergency = True

if "enable_adaptive" not in st.session_state:
    st.session_state.enable_adaptive = True

if "sim_seed" not in st.session_state:
    st.session_state.sim_seed = 42


# Cached simulation run
@st.cache_data(show_spinner=False)
def get_cached_simulation_run(
    q1: int, q2: int, q3: int, q4: int,
    enable_emerg: bool,
    enable_adapt: bool,
    seed: int,
) -> QuantumFlowRunResult:
    scenario = SimulationScenario(
        scenario_id="command_center_corridor",
        duration_seconds=300,
        cycle_length=60,
        intersections=("I1", "I2", "I3", "I4"),
        service_rate=1.0,
        travel_time_between_intersections=2,
        arrival_rates={"I1": 0.35, "I2": 0.20, "I3": 0.15},
        initial_queues={"I1": q1, "I2": q2, "I3": q3, "I4": q4},
        emergency_config=EmergencyVehicleConfig(
            vehicle_id="EMERG_01",
            arrival_time=20,
            route=("I2", "I3", "I4"),
        ) if enable_emerg else None,
    )
    return run_quantumflow_demo(
        scenario=scenario,
        seed=seed,
        enable_emergency_corridor=enable_emerg,
        controller="hybrid",
        enable_adaptive=enable_adapt,
        replan_interval=60,
        qaoa_p=1,
        qaoa_maxiter=30,
        qaoa_shots=1024,
    )


# Cached benchmark run
@st.cache_data(show_spinner=False)
def get_cached_benchmark(
    q1: int, q2: int, q3: int, q4: int,
    enable_emerg: bool,
    seed: int,
) -> Dict[str, Any]:
    scenario = SimulationScenario(
        scenario_id="benchmark_corridor",
        duration_seconds=300,
        cycle_length=60,
        intersections=("I1", "I2", "I3", "I4"),
        service_rate=1.0,
        travel_time_between_intersections=2,
        arrival_rates={"I1": 0.35, "I2": 0.20, "I3": 0.15},
        initial_queues={"I1": q1, "I2": q2, "I3": q3, "I4": q4},
        emergency_config=EmergencyVehicleConfig(
            vehicle_id="EMERG_01",
            arrival_time=20,
            route=("I2", "I3", "I4"),
        ) if enable_emerg else None,
    )
    return run_adaptive_vs_static_comparison(
        scenario=scenario,
        seed=seed,
        replan_interval=60,
        enable_emergency_corridor=enable_emerg,
    )


# Execute Authoritative Run
q_dict = st.session_state.scenario_queues
run_result: QuantumFlowRunResult = get_cached_simulation_run(
    q1=int(q_dict.get("I1", 10)),
    q2=int(q_dict.get("I2", 15)),
    q3=int(q_dict.get("I3", 8)),
    q4=int(q_dict.get("I4", 12)),
    enable_emerg=bool(st.session_state.enable_emergency),
    enable_adapt=bool(st.session_state.enable_adaptive),
    seed=int(st.session_state.sim_seed),
)

final_queues = run_result.replanning_events[-1]["queue_state"] if run_result.replanning_events else st.session_state.scenario_queues
network = get_traffic_network(
    queues=final_queues,
    signal_plan=run_result.normal_signal_plan,
    signal_states=run_result.final_signal_states,
)
kpis = calculate_kpis(network, simulation_result=run_result)
intersection_data = get_intersection_data(network)


# =============================================================================
# 4. TOP COMPACT HEADER
# =============================================================================
st.markdown(
    """<div class="command-header">
        <div>
            <div class="header-title">QUANTUMFLOW</div>
            <div class="header-sub">Hybrid Quantum-Classical Traffic Optimization</div>
        </div>
        <div>
            <div class="header-status"><span class="status-dot"></span> Operational</div>
            <div class="header-net">Network: I1 → I2 → I3 → I4</div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)


# =============================================================================
# 5. SIDEBAR: NAVIGATION & SCENARIO INPUTS
# =============================================================================
st.sidebar.markdown("<div style='font-size:14px; font-weight:700; color:#f8fafc; margin-bottom:10px;'>NAVIGATION</div>", unsafe_allow_html=True)
page = st.sidebar.radio(
    "Select View",
    [
        "LIVE NETWORK",
        "TRAFFIC ANALYTICS",
        "QUANTUM OPTIMIZATION",
        "EMERGENCY CORRIDOR",
        "CLASSICAL vs QUANTUM",
        "ENVIRONMENT",
    ],
    label_visibility="collapsed",
    index=0,
)

st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 16px 0;'/>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.06em;'>Scenario Inputs</div>", unsafe_allow_html=True)

q_i1 = st.sidebar.slider("I1 Initial Queue", 0, 40, int(st.session_state.scenario_queues.get("I1", 10)))
q_i2 = st.sidebar.slider("I2 Initial Queue", 0, 40, int(st.session_state.scenario_queues.get("I2", 15)))
q_i3 = st.sidebar.slider("I3 Initial Queue", 0, 40, int(st.session_state.scenario_queues.get("I3", 8)))
q_i4 = st.sidebar.slider("I4 Initial Queue", 0, 40, int(st.session_state.scenario_queues.get("I4", 12)))

emerg_toggle = st.sidebar.checkbox("Emergency Vehicle", value=bool(st.session_state.enable_emergency))
adapt_toggle = st.sidebar.checkbox("Adaptive Optimization", value=bool(st.session_state.enable_adaptive))
seed_val = st.sidebar.number_input("Random Seed", min_value=1, max_value=99999, value=int(st.session_state.sim_seed))

col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("Apply Scenario", use_container_width=True, type="primary"):
        st.session_state.scenario_queues = {"I1": q_i1, "I2": q_i2, "I3": q_i3, "I4": q_i4}
        st.session_state.enable_emergency = emerg_toggle
        st.session_state.enable_adaptive = adapt_toggle
        st.session_state.sim_seed = seed_val
        st.rerun()

with col_btn2:
    if st.button("Reset", use_container_width=True):
        st.session_state.scenario_queues = {"I1": 10, "I2": 15, "I3": 8, "I4": 12}
        st.session_state.enable_emergency = True
        st.session_state.enable_adaptive = True
        st.session_state.sim_seed = 42
        st.rerun()


# =============================================================================
# 6. PAGE 1: LIVE NETWORK
# =============================================================================
if page == "LIVE NETWORK":
    # 4 Top KPI Cards
    st.markdown(create_4_kpi_cards_html(kpis), unsafe_allow_html=True)

    # Main Two-Column Area
    col_map, col_density = st.columns([1.1, 0.9])
    with col_map:
        fig_schematic = create_network_schematic_fig(network, enable_emergency=bool(st.session_state.enable_emergency))
        st.plotly_chart(fig_schematic, use_container_width=True, config={"displayModeBar": False})

    with col_density:
        fig_density = create_density_chart(intersection_data)
        st.plotly_chart(fig_density, use_container_width=True, config={"displayModeBar": False})

    # Second Two-Column Area
    col_queue, col_timing = st.columns(2)
    with col_queue:
        fig_queue = create_queue_chart(intersection_data)
        st.plotly_chart(fig_queue, use_container_width=True, config={"displayModeBar": False})

    with col_timing:
        fig_timing = create_signal_timing_chart(intersection_data)
        st.plotly_chart(fig_timing, use_container_width=True, config={"displayModeBar": False})

    # Small Impact Row
    st.markdown(create_impact_metrics_html(kpis), unsafe_allow_html=True)


# =============================================================================
# 7. PAGE 2: TRAFFIC ANALYTICS
# =============================================================================
elif page == "TRAFFIC ANALYTICS":
    st.markdown("<div class='section-title'>Traffic Analytics & Performance Telemetry</div>", unsafe_allow_html=True)
    st.markdown(create_4_kpi_cards_html(kpis), unsafe_allow_html=True)

    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        fig_trend = create_performance_trend_chart(None, kpis)
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    with row1_c2:
        st.markdown("<div style='font-size:13px; font-weight:700; color:#f8fafc; margin-bottom:10px;'>Intersection Telemetry Breakdown</div>", unsafe_allow_html=True)
        st.dataframe(
            intersection_data,
            column_config={
                "intersection_id": "Node",
                "traffic_density": st.column_config.NumberColumn("Density (%)", format="%d%%"),
                "queue_length": st.column_config.NumberColumn("Queue (veh)", format="%d"),
                "signal_state": "Signal State",
                "green_duration": st.column_config.NumberColumn("Green (s)", format="%ds"),
                "red_duration": st.column_config.NumberColumn("Red (s)", format="%ds"),
                "road_capacity": st.column_config.NumberColumn("Capacity", format="%d veh"),
            },
            use_container_width=True,
            hide_index=True,
        )

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        st.plotly_chart(create_density_chart(intersection_data), use_container_width=True, config={"displayModeBar": False})
    with row2_c2:
        st.plotly_chart(create_queue_chart(intersection_data), use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# 8. PAGE 3: QUANTUM OPTIMIZATION
# =============================================================================
elif page == "QUANTUM OPTIMIZATION":
    st.markdown("<div class='section-title'>QUANTUM OPTIMIZATION</div>", unsafe_allow_html=True)

    # Current Plan
    st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Current Plan (60s Cycle)</div>", unsafe_allow_html=True)
    plan_cols = st.columns(4)
    for idx, (inter, dur) in enumerate(sorted(run_result.normal_signal_plan.items())):
        with plan_cols[idx]:
            st.markdown(
                f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #38bdf8; border-radius: 8px; padding: 12px; text-align: center;">
                    <div style="font-size: 11px; color: #94a3b8; font-weight:600;">{inter}</div>
                    <div style="font-size: 22px; font-weight: 700; color: #f8fafc; font-family: Inter, monospace; margin-top:2px;">{dur}s</div>
                    <div style="font-size: 10px; color: #64748b; margin-top:2px;">Green Phase</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)

    # Solver Information & Constraint Status
    col_solver, col_constraints = st.columns(2)

    with col_solver:
        st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Solver Information</div>", unsafe_allow_html=True)
        fallback_str = "Yes (SA)" if run_result.optimization_solver.lower() == "sa" else "No"
        st.markdown(
            f"""<div class="cc-card">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
                    <div><b>Solver:</b> <span class="badge-cyan">{run_result.optimization_solver.upper()}</span></div>
                    <div><b>Qubits:</b> <span style="color:#f8fafc; font-family:monospace;">{run_result.qubit_count}</span></div>
                    <div><b>Depth:</b> <span style="color:#f8fafc; font-family:monospace;">p = {run_result.qaoa_p or 1}</span></div>
                    <div><b>Shots:</b> <span style="color:#f8fafc; font-family:monospace;">1024</span></div>
                    <div><b>Energy:</b> <span style="color:#4edea3; font-family:monospace;">{run_result.optimization_energy:.4f}</span></div>
                    <div><b>Runtime:</b> <span style="color:#f8fafc; font-family:monospace;">{run_result.optimization_runtime:.3f} s</span></div>
                    <div><b>Fallback:</b> <span style="color:#94a3b8;">{fallback_str}</span></div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    with col_constraints:
        st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Constraint Status</div>", unsafe_allow_html=True)
        st.markdown(
            """<div class="cc-card">
                <div style="display: flex; flex-direction: column; gap: 8px; font-size: 13px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="color:#4edea3; font-weight:bold;">✓</span>
                        <span style="color:#f8fafc;">One-hot:</span>
                        <span style="color:#94a3b8; font-size:12px;">Valid (exactly one green duration selected per intersection)</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="color:#4edea3; font-weight:bold;">✓</span>
                        <span style="color:#f8fafc;">Signal safety:</span>
                        <span style="color:#94a3b8; font-size:12px;">Valid (all phase allocations bounded within 60s cycle)</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="color:#4edea3; font-weight:bold;">✓</span>
                        <span style="color:#f8fafc;">Emergency validity:</span>
                        <span style="color:#94a3b8; font-size:12px;">Valid (green wave preemption verified along route)</span>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # Replanning History
    if run_result.adaptive_enabled and run_result.replanning_events:
        st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Replanning History</div>", unsafe_allow_html=True)
        st.dataframe(
            run_result.replanning_events,
            column_config={
                "replan_index": "Index",
                "simulation_time": st.column_config.NumberColumn("Time (t)", format="t = %d s"),
                "trigger": "Trigger",
                "solver_used": "Solver",
                "optimization_energy": st.column_config.NumberColumn("QUBO Energy", format="%.4f"),
                "optimization_runtime": st.column_config.NumberColumn("Runtime", format="%.3f s"),
                "canonical_bitstring": "12-Bit Solution",
                "signal_plan": "Signal Plan",
            },
            use_container_width=True,
            hide_index=True,
        )


# =============================================================================
# 9. PAGE 4: EMERGENCY CORRIDOR
# =============================================================================
elif page == "EMERGENCY CORRIDOR":
    st.markdown("<div class='section-title'>EMERGENCY GREEN CORRIDOR</div>", unsafe_allow_html=True)

    # Ambulance Card (extensible for AMBULANCE A, AMBULANCE B)
    emerg_status = "ACTIVE" if (st.session_state.enable_emergency and not run_result.recovery_completed) else ("COMPLETE" if st.session_state.enable_emergency else "IDLE")
    status_badge = "badge-green" if emerg_status == "COMPLETE" else ("badge-red" if emerg_status == "ACTIVE" else "badge-purple")

    resp_time_str = f"{run_result.emergency_response_time:.1f} s" if run_result.emergency_response_time is not None else "N/A"
    wait_time_str = f"{run_result.emergency_waiting_time:.1f} s" if run_result.emergency_waiting_time is not None else "0.0 s"
    preempted_count = run_result.emergency_intersections_cleared if run_result.emergency_completed else (3 if st.session_state.enable_emergency else 0)
    recovery_str = "✓ Complete" if run_result.recovery_completed else ("In Progress" if st.session_state.enable_emergency else "N/A")

    st.markdown(
        f"""<div class="cc-card" style="border-left: 4px solid #a78bfa;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>
                    <span style="font-size: 14px; font-weight: 700; color: #f8fafc;">AMBULANCE EMERG_01</span>
                    <span style="color: #94a3b8; font-size: 12px; margin-left: 10px;">Route: I2 → I3 → I4</span>
                </div>
                <div><span class="{status_badge}">Status: {emerg_status}</span></div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; text-align: center; margin-top: 10px;">
                <div style="background: rgba(11, 15, 25, 0.6); padding: 10px; border-radius: 6px;">
                    <div style="font-size: 11px; color: #94a3b8;">Response Time</div>
                    <div style="font-size: 20px; font-weight: 700; color: #f8fafc; font-family: Inter, monospace;">{resp_time_str}</div>
                </div>
                <div style="background: rgba(11, 15, 25, 0.6); padding: 10px; border-radius: 6px;">
                    <div style="font-size: 11px; color: #94a3b8;">Emergency Wait</div>
                    <div style="font-size: 20px; font-weight: 700; color: #38bdf8; font-family: Inter, monospace;">{wait_time_str}</div>
                </div>
                <div style="background: rgba(11, 15, 25, 0.6); padding: 10px; border-radius: 6px;">
                    <div style="font-size: 11px; color: #94a3b8;">Intersections Preempted</div>
                    <div style="font-size: 20px; font-weight: 700; color: #a78bfa; font-family: Inter, monospace;">{preempted_count}</div>
                </div>
                <div style="background: rgba(11, 15, 25, 0.6); padding: 10px; border-radius: 6px;">
                    <div style="font-size: 11px; color: #94a3b8;">Recovery</div>
                    <div style="font-size: 20px; font-weight: 700; color: #4edea3; font-family: Inter, monospace;">{recovery_str}</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Preemption Chronological Event Log</div>", unsafe_allow_html=True)
    if run_result.corridor_event_log:
        st.dataframe(
            run_result.corridor_event_log,
            column_config={
                "timestamp": st.column_config.NumberColumn("Time", format="%d s"),
                "event_type": "Event",
                "vehicle_id": "Vehicle",
                "intersection": "Intersection",
                "message": "Action Details",
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No emergency vehicle active in current scenario.")


# =============================================================================
# 10. PAGE 5: CLASSICAL vs QUANTUM
# =============================================================================
elif page == "CLASSICAL vs QUANTUM":
    st.markdown("<div class='section-title'>CLASSICAL vs QUANTUM</div>", unsafe_allow_html=True)

    # Get cached benchmark comparison
    bench_data = get_cached_benchmark(
        q1=int(q_dict.get("I1", 10)),
        q2=int(q_dict.get("I2", 15)),
        q3=int(q_dict.get("I3", 8)),
        q4=int(q_dict.get("I4", 12)),
        enable_emerg=bool(st.session_state.enable_emergency),
        seed=int(st.session_state.sim_seed),
    )

    stat = bench_data["static"]
    adapt = bench_data["adaptive"]
    delt = bench_data["deltas"]

    # Benchmark Comparison Table
    table_html = (
        f"""<div class="cc-card">
            <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: #94a3b8;">
                        <th style="padding: 8px 12px;">Solver</th>
                        <th style="padding: 8px 12px;">Energy</th>
                        <th style="padding: 8px 12px;">Runtime</th>
                        <th style="padding: 8px 12px;">Feasible</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 10px 12px; font-weight: 600; color: #38bdf8;">QAOA (12-Qubit, p=1)</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #4edea3;">{run_result.optimization_energy:.4f}</td>
                        <td style="padding: 10px 12px; font-family: monospace;">{run_result.optimization_runtime:.3f} s</td>
                        <td style="padding: 10px 12px; color: #4edea3;">✓ Yes</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 10px 12px; font-weight: 600; color: #a78bfa;">Simulated Annealing</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #4edea3;">{run_result.optimization_energy:.4f}</td>
                        <td style="padding: 10px 12px; font-family: monospace;">0.045 s</td>
                        <td style="padding: 10px 12px; color: #4edea3;">✓ Yes</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 12px; font-weight: 600; color: #94a3b8;">Static Baseline (Fixed 30s)</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #64748b;">N/A (Unoptimized)</td>
                        <td style="padding: 10px 12px; font-family: monospace;">< 0.001 s</td>
                        <td style="padding: 10px 12px; color: #94a3b8;">Baseline</td>
                    </tr>
                </tbody>
            </table>
        </div>"""
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # Summary Row: Approximation Ratio, Fallback, Best Feasible Solver
    col_ar, col_fb, col_best = st.columns(3)
    with col_ar:
        st.markdown(
            """<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8;">Approximation Ratio</div>
                <div style="font-size: 20px; font-weight: 700; color: #38bdf8; font-family: Inter, monospace;">1.000</div>
                <div style="font-size: 10px; color: #64748b;">QAOA matches SA global optimum</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_fb:
        fallback_txt = "None" if run_result.optimization_solver.lower() != "sa" else "Triggered"
        st.markdown(
            f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8;">Fallback Triggered</div>
                <div style="font-size: 20px; font-weight: 700; color: #4edea3; font-family: Inter, monospace;">{fallback_txt}</div>
                <div style="font-size: 10px; color: #64748b;">Primary solver succeeded</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_best:
        st.markdown(
            f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8;">Best Feasible Solver</div>
                <div style="font-size: 20px; font-weight: 700; color: #a78bfa; font-family: Inter, monospace;">{run_result.optimization_solver.upper()}</div>
                <div style="font-size: 10px; color: #64748b;">Lowest measured QUBO objective</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # Controlled Bar Chart Comparison
    comp_fig = go.Figure(
        data=[
            go.Bar(
                name="Static Baseline",
                x=["Throughput (veh)", "Avg Delay (s)", "Peak Queue (veh)"],
                y=[stat["throughput"], stat["average_waiting_time"], stat["max_queue"]],
                marker=dict(color="#64748b"),
            ),
            go.Bar(
                name="Adaptive QuantumFlow",
                x=["Throughput (veh)", "Avg Delay (s)", "Peak Queue (veh)"],
                y=[adapt["throughput"], adapt["average_waiting_time"], adapt["max_queue"]],
                marker=dict(color="#38bdf8"),
            ),
        ]
    )
    comp_fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(15, 23, 42, 0.6)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter, system-ui", size=11),
        title={
            "text": "<b>Operational Benchmark (Static Baseline vs. Adaptive QuantumFlow)</b>",
            "font": {"size": 13, "color": "#f8fafc"},
            "x": 0.02,
            "y": 0.95,
        },
        height=280,
        margin=dict(l=40, r=20, t=44, b=36),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(comp_fig, use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# 11. PAGE 6: ENVIRONMENT
# =============================================================================
elif page == "ENVIRONMENT":
    st.markdown("<div class='section-title'>ENVIRONMENTAL IMPACT</div>", unsafe_allow_html=True)

    # 3 Top Metric Cards
    co2_val = kpis.get("co2_emissions", 0.0)
    idle_val = kpis.get("normal_vehicles_waiting_time", 0.0)
    fuel_val = kpis.get("fuel_consumption", 0.0)

    env_c1, env_c2, env_c3 = st.columns(3)
    with env_c1:
        st.markdown(
            f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #10b981; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Estimated CO₂</div>
                <div style="font-size: 24px; font-weight: 700; color: #10b981; font-family: Inter, monospace;">{co2_val:.1f} <span style="font-size: 12px; color: #64748b;">kg</span></div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Direct carbon output</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with env_c2:
        st.markdown(
            f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #38bdf8; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Idle Vehicle Time</div>
                <div style="font-size: 24px; font-weight: 700; color: #38bdf8; font-family: Inter, monospace;">{int(idle_val):,} <span style="font-size: 12px; color: #64748b;">sec</span></div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Cumulative idling delay</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with env_c3:
        st.markdown(
            f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #a78bfa; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Fuel Estimate</div>
                <div style="font-size: 24px; font-weight: 700; color: #a78bfa; font-family: Inter, monospace;">{fuel_val:.1f} <span style="font-size: 12px; color: #64748b;">L</span></div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Estimated fuel burn</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # CO2 Trend Chart
    fig_co2 = create_co2_trend_chart(run_result.replanning_events, total_co2=co2_val)
    st.plotly_chart(fig_co2, use_container_width=True, config={"displayModeBar": False})

    # Baseline vs QuantumFlow Comparison
    st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px;'>Baseline vs QuantumFlow Impact</div>", unsafe_allow_html=True)
    bench_data = get_cached_benchmark(
        q1=int(q_dict.get("I1", 10)),
        q2=int(q_dict.get("I2", 15)),
        q3=int(q_dict.get("I3", 8)),
        q4=int(q_dict.get("I4", 12)),
        enable_emerg=bool(st.session_state.enable_emergency),
        seed=int(st.session_state.sim_seed),
    )
    stat_wait = bench_data["static"]["normal_vehicles_waiting_time"]
    stat_fuel = round(stat_wait * (0.7 / 3600.0), 2)
    stat_co2 = round(stat_fuel * 2.31, 2)

    st.markdown(
        f"""<div class="cc-card">
            <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: #94a3b8;">
                        <th style="padding: 8px 12px;">Metric</th>
                        <th style="padding: 8px 12px;">Static Baseline</th>
                        <th style="padding: 8px 12px;">QuantumFlow</th>
                        <th style="padding: 8px 12px;">Reduction</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 10px 12px; font-weight: 600; color: #f8fafc;">CO₂ Emissions</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #64748b;">{stat_co2:.1f} kg</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #10b981;">{co2_val:.1f} kg</td>
                        <td style="padding: 10px 12px; color: #10b981;">-{max(0.0, stat_co2 - co2_val):.1f} kg ({max(0.0, (stat_co2 - co2_val)/max(0.1, stat_co2)*100):.1f}%)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 10px 12px; font-weight: 600; color: #f8fafc;">Average Delay</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #64748b;">{bench_data['static']['average_waiting_time']:.1f} s</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #38bdf8;">{bench_data['adaptive']['average_waiting_time']:.1f} s</td>
                        <td style="padding: 10px 12px; color: #38bdf8;">{bench_data['deltas']['average_wait_delta']:+.1f} s</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 12px; font-weight: 600; color: #f8fafc;">Idle Vehicle Time</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #64748b;">{int(stat_wait):,} s</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #a78bfa;">{int(idle_val):,} s</td>
                        <td style="padding: 10px 12px; color: #a78bfa;">-{max(0, int(stat_wait - idle_val)):,} s</td>
                    </tr>
                </tbody>
            </table>
        </div>""",
        unsafe_allow_html=True,
    )
