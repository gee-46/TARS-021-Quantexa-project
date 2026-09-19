"""Plotly visualization charts and styled KPI cards for QuantumFlow traffic analytics.

Provides reusable functions for:
- 4 Uniform KPI Cards (Throughput, Avg Wait, Peak Queue, Emergency Response)
- Network Schematic Diagram (I1 -> I2 -> I3 -> I4 corridor)
- Traffic density bar chart (I1 -> I4)
- Queue length bar chart (I1 -> I4)
- Signal timing chart (Green vs Red phase allocation)
- Multi-metric performance trend time-series chart
- CO2 Emissions trend chart
- System Impact metrics row (Person Delay, Fairness, CO2)
"""

from typing import List, Dict, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DARK_BG = "rgba(15, 23, 42, 0.6)"
GRID_COLOR = "rgba(255, 255, 255, 0.07)"
TEXT_COLOR = "#94a3b8"
TEXT_WHITE = "#f8fafc"
CYAN = "#38bdf8"
GREEN = "#4edea3"
RED = "#f87171"
AMBER = "#fbbf24"
PURPLE = "#a78bfa"
INDIGO = "#6366f1"


def _apply_dark_layout(fig: go.Figure, title: str, height: int = 270) -> go.Figure:
    """Apply consistent command-center dark styling to a Plotly figure."""
    fig.update_layout(
        title={
            "text": f"<b>{title}</b>",
            "font": {"size": 13, "color": TEXT_WHITE, "family": "Inter, system-ui, sans-serif"},
            "x": 0.02,
            "y": 0.96,
        },
        paper_bgcolor=DARK_BG,
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={"family": "Inter, system-ui, sans-serif", "color": TEXT_COLOR, "size": 11},
        margin=dict(l=42, r=24, t=44, b=36),
        height=height,
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_size=11,
            font_color=TEXT_WHITE,
            bordercolor="rgba(255,255,255,0.15)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color=TEXT_COLOR),
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=TEXT_COLOR, size=11),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=TEXT_COLOR, size=11),
    )
    return fig


def create_density_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a clean bar chart displaying traffic density for each intersection."""
    intersections = [d["intersection_id"] for d in intersection_data]
    densities = [d["traffic_density"] for d in intersection_data]

    colors = []
    for dens in densities:
        if dens >= 70:
            colors.append(RED)
        elif dens >= 40:
            colors.append(AMBER)
        else:
            colors.append(GREEN)

    fig = go.Figure(
        data=[
            go.Bar(
                x=intersections,
                y=densities,
                marker=dict(
                    color=colors,
                    line=dict(color="rgba(255, 255, 255, 0.15)", width=1),
                    opacity=0.9,
                ),
                text=[f"{d}%" for d in densities],
                textposition="outside",
                textfont=dict(color=TEXT_WHITE, size=11, family="Inter, monospace"),
                hovertemplate="<b>%{x}</b><br>Traffic Density: %{y}%<extra></extra>",
            )
        ]
    )

    fig.add_hline(
        y=70,
        line_dash="dot",
        line_color="rgba(248, 113, 113, 0.5)",
        annotation_text="70% Threshold",
        annotation_position="top right",
        annotation_font=dict(size=9, color=RED),
    )

    fig.update_yaxes(title_text="Density (%)", range=[0, max(85, max(densities) + 20)])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Traffic Density by Intersection", height=270)


def create_queue_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a clean bar chart of queue lengths for the intersections."""
    intersections = [d["intersection_id"] for d in intersection_data]
    queues = [d["queue_length"] for d in intersection_data]

    fig = go.Figure(
        data=[
            go.Bar(
                x=intersections,
                y=queues,
                marker=dict(
                    color=CYAN,
                    line=dict(color="rgba(56, 189, 248, 0.3)", width=1),
                    opacity=0.88,
                ),
                text=[f"{q} veh" for q in queues],
                textposition="outside",
                textfont=dict(color=TEXT_WHITE, size=11, family="Inter, monospace"),
                hovertemplate="<b>%{x}</b><br>Queue: %{y} vehicles<extra></extra>",
            )
        ]
    )

    fig.update_yaxes(title_text="Queue (vehicles)", range=[0, max(15, max(queues) + 8)])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Queue Length by Intersection", height=270)


def create_signal_timing_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a grouped bar chart showing Green vs Red duration."""
    intersections = [d["intersection_id"] for d in intersection_data]
    green_times = [d["green_duration"] for d in intersection_data]
    red_times = [d["red_duration"] for d in intersection_data]
    signals = [d.get("signal_state", "GREEN") for d in intersection_data]

    fig = go.Figure(
        data=[
            go.Bar(
                name="Green (s)",
                x=intersections,
                y=green_times,
                marker=dict(color=GREEN, opacity=0.88),
                hovertemplate="<b>%{x}</b><br>Green Phase: %{y}s<extra></extra>",
            ),
            go.Bar(
                name="Red (s)",
                x=intersections,
                y=red_times,
                marker=dict(color=RED, opacity=0.75),
                hovertemplate="<b>%{x}</b><br>Red Phase: %{y}s<extra></extra>",
            ),
        ]
    )

    for idx, (nid, sig) in enumerate(zip(intersections, signals)):
        sig_color = GREEN if ("GREEN" in sig or sig == "NORMAL") else RED
        fig.add_annotation(
            x=nid,
            y=max(green_times[idx], red_times[idx]) + 5,
            text=f"● {sig}",
            showarrow=False,
            font=dict(color=sig_color, size=10, family="Inter, monospace"),
        )

    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Seconds / Cycle (60s)", range=[0, max(max(green_times), max(red_times)) + 14])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Signal Phase Timing", height=270)


def create_network_schematic_fig(network: Any, enable_emergency: bool = True) -> go.Figure:
    """Create a clean, crystal-clear horizontal arterial corridor schematic (I1 -> I2 -> I3 -> I4)."""
    node_ids = ["I1", "I2", "I3", "I4"]
    x_coords = [1, 2, 3, 4]
    y_coords = [0, 0, 0, 0]

    node_colors = []
    hover_texts = []
    labels = []

    for nid in node_ids:
        if hasattr(network, "nodes") and network.has_node(nid):
            data = network.nodes[nid]
            sig = str(data.get("signal_state", "GREEN")).upper()
            q = data.get("queue_length", 0)
            dur = data.get("green_duration", 30)
            dens = data.get("traffic_density", 0)
        else:
            sig = "GREEN"
            q = 10
            dur = 30
            dens = 25

        if "GREEN" in sig or sig == "NORMAL":
            node_colors.append(GREEN)
        elif "RED" in sig:
            node_colors.append(RED)
        else:
            node_colors.append(CYAN)

        labels.append(f"<b>{nid}</b><br><span style='font-size:10px;'>{q} veh | {dur}s</span>")
        hover_texts.append(
            f"<b>Intersection {nid}</b><br>"
            f"Signal State: {sig}<br>"
            f"Green Duration: {dur}s / 60s<br>"
            f"Queue Length: {q} veh<br>"
            f"Density: {dens}%"
        )

    fig = go.Figure()

    # Base Corridor Link Line
    fig.add_trace(
        go.Scatter(
            x=[1, 4],
            y=[0, 0],
            mode="lines",
            line=dict(color="rgba(148, 163, 184, 0.4)", width=5),
            hoverinfo="none",
            showlegend=False,
        )
    )

    # Emergency Corridor Route Highlight (I2 -> I3 -> I4)
    if enable_emergency:
        fig.add_trace(
            go.Scatter(
                x=[2, 4],
                y=[0, 0],
                mode="lines",
                line=dict(color=PURPLE, width=7, dash="solid"),
                name="Ambulance Corridor (I2 → I4)",
                hoverinfo="text",
                hovertext="Active Preemption Wave: I2 → I3 → I4",
            )
        )

    # Intersection Nodes
    fig.add_trace(
        go.Scatter(
            x=x_coords,
            y=y_coords,
            mode="markers+text",
            marker=dict(
                size=44,
                color=node_colors,
                line=dict(color="#ffffff", width=2),
                opacity=0.95,
            ),
            text=labels,
            textposition="bottom center",
            textfont=dict(color=TEXT_WHITE, size=11, family="Inter, system-ui"),
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False,
        )
    )

    # Small arrows indicating arterial flow direction
    for x in [1.5, 2.5, 3.5]:
        fig.add_annotation(
            x=x,
            y=0,
            text="➔",
            showarrow=False,
            font=dict(color="#cbd5e1", size=14),
        )

    fig.update_layout(
        title={
            "text": "<b>Simulated 4-Intersection Network</b> <span style='font-size:11px; color:#94a3b8;'>(I1 → I2 → I3 → I4)</span>",
            "font": {"size": 13, "color": TEXT_WHITE, "family": "Inter, system-ui, sans-serif"},
            "x": 0.02,
            "y": 0.96,
        },
        paper_bgcolor=DARK_BG,
        plot_bgcolor="rgba(0, 0, 0, 0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.4, 4.6]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.8, 0.6]),
        margin=dict(l=20, r=20, t=44, b=30),
        height=270,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color=TEXT_COLOR),
        ),
    )
    return fig


def create_performance_trend_chart(
    history_data: Optional[List[Dict[str, Any]]] = None,
    current_kpis: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a multi-metric time-series chart for delay, queue, and throughput."""
    if history_data is None:
        if current_kpis is None:
            current_kpis = {
                "avg_waiting_time": 45.0,
                "avg_queue_length": 8.0,
                "throughput": 211,
            }
        base_wait = float(current_kpis.get("avg_waiting_time", 45.0))
        base_queue = float(current_kpis.get("avg_queue_length", 8.0))
        base_tp = float(current_kpis.get("throughput", 211))

        steps = ["T-4m", "T-3m", "T-2m", "T-1m", "Live"]
        wait_series = [
            round(base_wait * 1.25, 1),
            round(base_wait * 1.15, 1),
            round(base_wait * 1.08, 1),
            round(base_wait * 1.02, 1),
            round(base_wait, 1),
        ]
        queue_series = [
            round(base_queue * 1.4, 1),
            round(base_queue * 1.25, 1),
            round(base_queue * 1.1, 1),
            round(base_queue * 1.05, 1),
            round(base_queue, 1),
        ]
        tp_series = [
            round(base_tp * 0.75),
            round(base_tp * 0.85),
            round(base_tp * 0.92),
            round(base_tp * 0.98),
            round(base_tp),
        ]
    else:
        steps = [d.get("time", f"T{i}") for i, d in enumerate(history_data)]
        wait_series = [d.get("avg_waiting_time", 0) for d in history_data]
        queue_series = [d.get("avg_queue_length", 0) for d in history_data]
        tp_series = [d.get("throughput", 0) for d in history_data]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=wait_series,
            mode="lines+markers",
            name="Avg Delay (s)",
            line=dict(color=CYAN, width=2.2),
            marker=dict(size=5, color=CYAN),
            hovertemplate="%{x}: %{y:.1f} s<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=queue_series,
            mode="lines+markers",
            name="Avg Queue (veh)",
            line=dict(color=AMBER, width=2.2, dash="dash"),
            marker=dict(size=5, color=AMBER),
            hovertemplate="%{x}: %{y:.1f} veh<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=tp_series,
            mode="lines+markers",
            name="Throughput (veh)",
            line=dict(color=GREEN, width=2),
            marker=dict(size=4, color=GREEN),
            hovertemplate="%{x}: %{y:.0f} veh<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_xaxes(title_text="Time Window")
    fig.update_yaxes(title_text="Delay (s) / Queue (veh)", secondary_y=False)
    fig.update_yaxes(title_text="Throughput (vehicles)", secondary_y=True, showgrid=False)

    return _apply_dark_layout(fig, "Traffic Telemetry Trends (Delay, Queue & Throughput)", height=280)


def create_co2_trend_chart(replanning_events: Optional[List[Dict[str, Any]]] = None, total_co2: float = 12.4) -> go.Figure:
    """Create a line chart showing estimated CO2 emissions across simulation time."""
    if replanning_events and len(replanning_events) > 1:
        times = [f"t={e['simulation_time']}s" for e in replanning_events]
        # Cumulative CO2 profile
        n = len(times)
        co2_vals = [round((i + 1) / n * total_co2, 2) for i in range(n)]
    else:
        times = ["t=0s", "t=60s", "t=120s", "t=180s", "t=240s", "t=300s"]
        co2_vals = [0.0, round(total_co2 * 0.18, 2), round(total_co2 * 0.38, 2), round(total_co2 * 0.58, 2), round(total_co2 * 0.79, 2), total_co2]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=times,
                y=co2_vals,
                mode="lines+markers",
                name="CO₂ Emissions",
                line=dict(color="#10b981", width=2.5),
                marker=dict(size=6, color="#10b981"),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.12)",
                hovertemplate="%{x}: %{y:.2f} kg CO₂<extra></extra>",
            )
        ]
    )
    fig.update_xaxes(title_text="Simulation Timestamp")
    fig.update_yaxes(title_text="Cumulative CO₂ (kg)")
    return _apply_dark_layout(fig, "Estimated CO₂ Emissions Over Simulation Time", height=280)


def create_4_kpi_cards_html(kpis: Dict[str, Any]) -> str:
    """Generate exact 4 primary KPI cards with uniform dimensions, styling, and typography."""
    tp_val = f"{int(kpis.get('throughput', 0)):,}"
    wait_val = f"{kpis.get('avg_waiting_time', 0.0):.1f} s"
    q_val = f"{int(kpis.get('max_queue', 0))}"
    emerg_raw = kpis.get("emergency_response_time")
    emerg_val = f"{float(emerg_raw):.1f} s" if emerg_raw is not None else "N/A"

    cards = [
        {"title": "THROUGHPUT", "value": tp_val, "subtitle": "vehicles", "accent": GREEN},
        {"title": "AVG WAIT", "value": wait_val, "subtitle": "per vehicle", "accent": CYAN},
        {"title": "PEAK QUEUE", "value": q_val, "subtitle": "vehicles", "accent": AMBER},
        {"title": "EMERGENCY", "value": emerg_val, "subtitle": "response", "accent": PURPLE},
    ]

    items = []
    for c in cards:
        html = (
            f'<div style="flex: 1 1 0; min-width: 140px; background: rgba(15, 23, 42, 0.75); '
            f'border: 1px solid rgba(255, 255, 255, 0.08); border-top: 3px solid {c["accent"]}; '
            f'border-radius: 8px; padding: 14px 16px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">'
            f'<div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 6px;">{c["title"]}</div>'
            f'<div style="font-size: 26px; font-weight: 700; color: #f8fafc; font-family: Inter, monospace; line-height: 1.1;">{c["value"]}</div>'
            f'<div style="font-size: 11px; color: #64748b; margin-top: 4px;">{c["subtitle"]}</div>'
            f'</div>'
        )
        items.append(html)

    cards_str = "".join(items)
    return f'<div style="display: flex; gap: 14px; width: 100%; margin-bottom: 18px;">{cards_str}</div>'


def create_impact_metrics_html(kpis: Dict[str, Any]) -> str:
    """Generate clean, non-overdecorated System Impact metrics row (Person Delay | Fairness | CO2)."""
    person_delay = kpis.get("person_delay", int(kpis.get("normal_vehicles_waiting_time", 0) * 1.4))
    fairness = kpis.get("fairness_index", 0.92)
    co2 = kpis.get("co2_emissions", 0.0)

    html = (
        f'<div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); '
        f'border-radius: 8px; padding: 14px 20px; margin-top: 14px; width: 100%;">'
        f'<div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 12px;">SYSTEM IMPACT</div>'
        f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; text-align: center;">'
        f'<div>'
        f'<div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Person Delay</div>'
        f'<div style="font-size: 20px; font-weight: 700; color: #f8fafc; font-family: Inter, monospace;">{int(person_delay):,} <span style="font-size: 11px; color: #64748b; font-weight: normal;">person-sec</span></div>'
        f'<div style="font-size: 10px; color: #64748b; margin-top: 2px;">Estimated total delay</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Fairness</div>'
        f'<div style="font-size: 20px; font-weight: 700; color: #38bdf8; font-family: Inter, monospace;">{fairness:.2f}</div>'
        f'<div style="font-size: 10px; color: #64748b; margin-top: 2px;">Jain Fairness Index</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">CO₂</div>'
        f'<div style="font-size: 20px; font-weight: 700; color: #4edea3; font-family: Inter, monospace;">{co2:.1f} <span style="font-size: 11px; color: #64748b; font-weight: normal;">kg</span></div>'
        f'<div style="font-size: 10px; color: #64748b; margin-top: 2px;">Estimated CO₂</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    return html
