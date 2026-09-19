"""QuantumFlow — Hybrid Quantum-Classical Traffic Signal Optimization Dashboard.

Seamlessly transitions from the WebThreads WebGL loader into the interactive multi-intersection dashboard.
"""

import streamlit as st
import json
from typing import Dict, Any

from frontend.component import webthreads_loader
from simulation.integration import (
    run_quantumflow_demo,
    compare_runs,
    create_canonical_demo_scenario,
    QuantumFlowRunResult,
    RunComparisonResult,
)
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig

st.set_page_config(
    page_title="QuantumFlow — Quantum Traffic Optimization",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 1. LOADER SESSION STATE & TRANSITION GATE
# -----------------------------------------------------------------------------
if "loader_complete" not in st.session_state:
    st.session_state.loader_complete = False

if not st.session_state.loader_complete:
    # Fullscreen immersive loader container
    st.markdown(
        """
        <style>
            .stAppHeader { display: none; }
            .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }
            header { visibility: hidden; }
            footer { visibility: hidden; }
            [data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Render WebThreads custom component
    status = webthreads_loader(key="quantumflow_webthreads_loader")

    if status == "LOADER_COMPLETE":
        st.session_state.loader_complete = True
        st.rerun()

    # Fallback skip button for quick navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➔ Skip Animation & Enter Dashboard", key="skip_loader_btn", use_container_width=True):
            st.session_state.loader_complete = True
            st.rerun()

    st.stop()


# -----------------------------------------------------------------------------
# 2. MAIN QUANTUMFLOW DASHBOARD
# -----------------------------------------------------------------------------

# Custom Styling for QuantumFlow UI
st.markdown(
    """
    <style>
        .quantum-header {
            background: linear-gradient(135deg, #100b2b 0%, #080614 100%);
            border: 1px solid rgba(138, 75, 255, 0.25);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        }
        .metric-card {
            background: rgba(18, 14, 38, 0.7);
            border: 1px solid rgba(168, 85, 247, 0.2);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #38bdf8;
            font-family: 'JetBrains Mono', monospace;
        }
        .stat-label {
            font-size: 0.8rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .delta-positive { color: #4ade80; font-weight: 600; }
        .delta-negative { color: #f87171; font-weight: 600; }
        .delta-neutral { color: #94a3b8; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Banner
st.markdown(
    """
    <div class="quantum-header">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="background: rgba(168, 85, 247, 0.2); border: 1px solid #a855f7; border-radius: 100px; padding: 4px 12px; font-size: 0.75rem; color: #c084fc; font-family: monospace;">
                    QUBO • 12-QUBIT QAOA • MICROSCOPIC SIMULATION
                </span>
                <h1 style="margin: 8px 0 4px 0; font-size: 2.2rem; font-weight: 800; letter-spacing: 0.05em; background: linear-gradient(90deg, #ffffff, #c084fc, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    QUANTUMFLOW
                </h1>
                <p style="margin: 0; color: #94a3b8; font-size: 0.95rem;">
                    Hybrid Quantum-Classical Multi-Intersection Traffic Signal Optimization & Dynamic Green Corridor
                </p>
            </div>
            <div style="text-align: right;">
                <span style="font-family: monospace; font-size: 0.8rem; color: #4ade80;">● SYSTEM OPERATIONAL</span><br/>
                <span style="font-size: 0.75rem; color: #64748b;">Grid: I1 → I2 → I3 → I4 (4 Intersections)</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Controls
st.sidebar.title("Configuration")
st.sidebar.markdown("---")

controller_choice = st.sidebar.selectbox(
    "Optimization Controller",
    options=["hybrid", "sa", "fixed", "rule"],
    format_func=lambda x: {
        "hybrid": "Hybrid QuantumFlow (QAOA + SA Fallback)",
        "sa": "Classical Simulated Annealing (dwave-neal)",
        "fixed": "Fixed-Time Baseline (30s everywhere)",
        "rule": "Rule-Based Actuated Controller",
    }[x],
    index=0,
)

enable_emergency = st.sidebar.checkbox(
    "Enable Dynamic Emergency Green Corridor",
    value=True,
    help="Activates real-time progressive signal preemption for emergency vehicle EMERG_01 along I2 -> I3 -> I4.",
)

seed_input = st.sidebar.number_input(
    "Deterministic Random Seed",
    min_value=1,
    max_value=999999,
    value=42,
    step=1,
    help="Controls demand realization and arrival generation reproducibility.",
)

duration_input = st.sidebar.slider(
    "Simulation Horizon (seconds)",
    min_value=60,
    max_value=600,
    value=300,
    step=60,
)

st.sidebar.markdown("---")
st.sidebar.subheader("Emergency Vehicle")
st.sidebar.markdown("**Vehicle ID:** `EMERG_01`")
st.sidebar.markdown("**Arrival Second:** $t = 20\\text{s}$")
st.sidebar.markdown("**Assigned Route:** `I2 → I3 → I4`")

st.sidebar.markdown("---")
if st.sidebar.button("↻ Replay WebThreads Loader", use_container_width=True):
    st.session_state.loader_complete = False
    st.rerun()

# -----------------------------------------------------------------------------
# 3. RUN BACKEND PIPELINE
# -----------------------------------------------------------------------------

# Construct Scenario
custom_scenario = SimulationScenario(
    scenario_id="canonical_phase15_demo",
    duration_seconds=int(duration_input),
    cycle_length=60,
    intersections=("I1", "I2", "I3", "I4"),
    service_rate=1.0,
    travel_time_between_intersections=2,
    arrival_rates={"I1": 0.35, "I2": 0.20, "I3": 0.15},
    initial_queues={"I1": 10, "I2": 15, "I3": 8, "I4": 12},
    emergency_config=EmergencyVehicleConfig(
        vehicle_id="EMERG_01",
        arrival_time=20,
        route=("I2", "I3", "I4"),
    ),
)

with st.spinner("Executing Quantum-Classical Optimization & Microscopic Simulation..."):
    # Run Active Configuration
    active_result: QuantumFlowRunResult = run_quantumflow_demo(
        scenario=custom_scenario,
        seed=int(seed_input),
        enable_emergency_corridor=enable_emergency,
        controller=controller_choice,
        qaoa_p=1,
        qaoa_maxiter=30,
        qaoa_shots=1024,
    )

    # Run Baseline (Corridor Disabled) for objective comparison
    baseline_result: QuantumFlowRunResult = run_quantumflow_demo(
        scenario=custom_scenario,
        seed=int(seed_input),
        enable_emergency_corridor=False,
        controller=controller_choice,
        qaoa_p=1,
        qaoa_maxiter=30,
        qaoa_shots=1024,
    )

    deltas: RunComparisonResult = compare_runs(baseline=baseline_result, quantumflow=active_result)

# -----------------------------------------------------------------------------
# 4. DASHBOARD PRESENTATION
# -----------------------------------------------------------------------------

# Top KPI Row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="stat-label">Throughput</div>
            <div class="stat-value">{active_result.throughput} <span style="font-size:0.9rem; color:#94a3b8;">veh</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Completed in {active_result.simulation_duration}s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="stat-label">Average Wait</div>
            <div class="stat-value">{active_result.average_waiting_time:.1f} <span style="font-size:0.9rem; color:#94a3b8;">s</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Per Vehicle</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="stat-label">Emergency Response</div>
            <div class="stat-value">{active_result.emergency_response_time:.1f} <span style="font-size:0.9rem; color:#94a3b8;">s</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Origin to Destination</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="stat-label">Max Queue Length</div>
            <div class="stat-value">{active_result.max_queue} <span style="font-size:0.9rem; color:#94a3b8;">veh</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Peak Congestion</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="stat-label">Recovery Status</div>
            <div class="stat-value" style="color:#4ade80;">{"RESTORED" if active_result.recovery_completed else "ACTIVE"}</div>
            <div style="font-size:0.75rem; color:#64748b;">Signals in Normal Mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br/>", unsafe_allow_html=True)

# Tabs for Detailed Breakdown
tab_overview, tab_comparison, tab_events, tab_raw = st.tabs([
    "🚦 Signal Plan & Optimization",
    "📊 Controlled Delta Comparison",
    "📜 Emergency Event Log",
    "🔍 JSON Telemetry",
])

with tab_overview:
    col_plan, col_opt = st.columns([1, 1])

    with col_plan:
        st.subheader("Decoded Normal Signal Plan")
        st.caption("Allocated green phase durations per 60-second cycle")

        plan_cols = st.columns(4)
        for idx, (inter, dur) in enumerate(sorted(active_result.normal_signal_plan.items())):
            with plan_cols[idx]:
                st.metric(
                    label=f"Intersection {inter}",
                    value=f"{dur}s Green",
                    delta=f"{60 - dur}s Red",
                    delta_color="off",
                )

        st.info("💡 Signal durations are evaluated offline by the QUBO solver. Emergency green waves dynamically override these signals during live vehicle transit without altering the baseline timing.")

    with col_opt:
        st.subheader("Optimization Telemetry")
        st.markdown(
            f"""
            - **Primary Solver:** `{active_result.optimization_solver}`
            - **Status:** `{active_result.optimization_status}`
            - **QUBO Energy:** `{active_result.optimization_energy:.4f}`
            - **Optimization Runtime:** `{active_result.optimization_runtime:.4f}s`
            - **Classical Fallback Used:** `{'Yes' if active_result.optimization_fallback_used else 'No (QAOA Accepted)'}`
            - **One-Hot Constraint Satisfied:** `{active_result.onehot_valid}`
            """
        )

with tab_comparison:
    st.subheader("Controlled Comparison: Corridor Enabled vs. Corridor Disabled (Baseline)")
    st.caption("Formula: Delta = Corridor Enabled - Baseline (Strictly factual arithmetic differences)")

    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    with d_col1:
        st.metric(
            label="Emergency Response Time Delta",
            value=f"{active_result.emergency_response_time:.1f}s",
            delta=f"{deltas.emergency_response_delta:+.1f}s" if deltas.emergency_response_delta is not None else "N/A",
            delta_color="inverse",
        )
    with d_col2:
        st.metric(
            label="Emergency Waiting Time Delta",
            value=f"{active_result.emergency_waiting_time:.1f}s",
            delta=f"{deltas.emergency_wait_delta:+.1f}s" if deltas.emergency_wait_delta is not None else "N/A",
            delta_color="inverse",
        )
    with d_col3:
        st.metric(
            label="Throughput Delta",
            value=f"{active_result.throughput} veh",
            delta=f"{deltas.throughput_delta:+d} veh",
            delta_color="normal",
        )
    with d_col4:
        st.metric(
            label="Normal Traffic Wait Delta",
            value=f"{active_result.normal_vehicles_waiting_time:.0f}s",
            delta=f"{deltas.normal_wait_delta:+.0f}s",
            delta_color="inverse",
        )

with tab_events:
    st.subheader("Chronological Emergency Corridor Event Log")
    if active_result.corridor_event_log:
        st.dataframe(
            active_result.corridor_event_log,
            column_config={
                "timestamp": st.column_config.NumberColumn("Second (t)", format="%d s"),
                "event_type": "Event Type",
                "vehicle_id": "Vehicle ID",
                "intersection": "Intersection",
                "message": "Lifecycle Details",
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No emergency preemption events recorded (Dynamic corridor was disabled for this run).")

with tab_raw:
    st.subheader("JSON Serialization Contract")
    st.json(active_result.to_dict())
