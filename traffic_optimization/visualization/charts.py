"""Plotly visualization charts for traffic analytics.

Provides reusable functions for:
- Traffic density bar chart
- Queue length bar chart
- Signal timing chart (green vs red duration)
- Multi-metric performance trend time-series chart
- KPI cards HTML generator
"""

from typing import List, Dict, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots


DARK_BG = "rgba(10, 14, 24, 0.4)"
GRID_COLOR = "rgba(255, 255, 255, 0.08)"
TEXT_COLOR = "#d1d5db"
CYAN = "#00f0ff"
GREEN = "#4edea3"
RED = "#ef4444"
AMBER = "#f59e0b"
PURPLE = "#a78bfa"


def _apply_dark_layout(fig: go.Figure, title: str, height: int = 340) -> go.Figure:
    """Apply consistent command-center dark styling to a Plotly figure."""
    fig.update_layout(
        title={
            "text": f"<b>{title}</b>",
            "font": {"size": 15, "color": "#f3f4f6", "family": "Inter, system-ui, sans-serif"},
            "x": 0.02,
            "y": 0.95,
        },
        paper_bgcolor=DARK_BG,
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={"family": "Inter, system-ui, sans-serif", "color": TEXT_COLOR, "size": 12},
        margin=dict(l=45, r=30, t=50, b=40),
        height=height,
        hoverlabel=dict(
            bgcolor="#111827",
            font_size=12,
            font_color="#f9fafb",
            bordercolor="rgba(255,255,255,0.2)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_COLOR),
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=TEXT_COLOR),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=TEXT_COLOR),
    )
    return fig


def create_density_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a bar chart displaying traffic density for each intersection."""
    intersections = [d["intersection_id"] for d in intersection_data]
    densities = [d["traffic_density"] for d in intersection_data]

    # Color code bars based on congestion levels
    colors = []
    for dens in densities:
        if dens >= 40:
            colors.append(RED)
        elif dens >= 30:
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
                    line=dict(color="rgba(255, 255, 255, 0.2)", width=1.5),
                    opacity=0.88,
                ),
                text=[f"{d}%" for d in densities],
                textposition="outside",
                textfont=dict(color="#f3f4f6", size=12, family="monospace"),
                hovertemplate="<b>Intersection %{x}</b><br>Traffic Density: %{y}%<extra></extra>",
            )
        ]
    )

    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="rgba(239, 68, 68, 0.6)",
        annotation_text="Congestion Threshold (50%)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=RED),
    )

    fig.update_yaxes(title_text="Density (%)", range=[0, max(60, max(densities) + 15)])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Traffic Density by Intersection")


def create_queue_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a bar chart of queue lengths for all six intersections."""
    intersections = [d["intersection_id"] for d in intersection_data]
    queues = [d["queue_length"] for d in intersection_data]

    fig = go.Figure(
        data=[
            go.Bar(
                x=intersections,
                y=queues,
                marker=dict(
                    color=CYAN,
                    line=dict(color="rgba(0, 240, 255, 0.4)", width=1.5),
                    opacity=0.85,
                ),
                text=[f"{q} veh" for q in queues],
                textposition="outside",
                textfont=dict(color="#f3f4f6", size=12, family="monospace"),
                hovertemplate="<b>Intersection %{x}</b><br>Queue Length: %{y} vehicles<extra></extra>",
            )
        ]
    )

    fig.update_yaxes(title_text="Queue (vehicles)", range=[0, max(15, max(queues) + 5)])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Queue Length by Intersection")


def create_signal_timing_chart(intersection_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a grouped bar chart showing Green vs Red duration and current active state."""
    intersections = [d["intersection_id"] for d in intersection_data]
    green_times = [d["green_duration"] for d in intersection_data]
    red_times = [d["red_duration"] for d in intersection_data]
    signals = [d["signal_state"] for d in intersection_data]

    fig = go.Figure(
        data=[
            go.Bar(
                name="Green Phase (s)",
                x=intersections,
                y=green_times,
                marker=dict(color=GREEN, opacity=0.85),
                hovertemplate="<b>%{x}</b><br>Green: %{y}s<extra></extra>",
            ),
            go.Bar(
                name="Red Phase (s)",
                x=intersections,
                y=red_times,
                marker=dict(color=RED, opacity=0.75),
                hovertemplate="<b>%{x}</b><br>Red: %{y}s<extra></extra>",
            ),
        ]
    )

    # Add annotations for current active state
    for idx, (nid, sig) in enumerate(zip(intersections, signals)):
        sig_color = GREEN if sig == "GREEN" else RED
        fig.add_annotation(
            x=nid,
            y=max(green_times[idx], red_times[idx]) + 6,
            text=f"● {sig}",
            showarrow=False,
            font=dict(color=sig_color, size=11, family="monospace"),
        )

    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Duration (seconds)", range=[0, max(max(green_times), max(red_times)) + 14])
    fig.update_xaxes(title_text="Intersection")
    return _apply_dark_layout(fig, "Signal Phase Timing & Active Status")


def create_performance_trend_chart(
    history_data: Optional[List[Dict[str, Any]]] = None,
    current_kpis: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a multi-metric time-series chart for delay, queue, and throughput.

    If history_data is not supplied, generates historical intervals leading up
    to current_kpis to show the baseline trend.
    """
    if history_data is None:
        # Generate baseline trend from current state
        if current_kpis is None:
            current_kpis = {
                "avg_waiting_time": 36.5,
                "avg_queue_length": 8.0,
                "traffic_throughput": 4800,
            }
        base_wait = current_kpis.get("avg_waiting_time", 35.0)
        base_queue = current_kpis.get("avg_queue_length", 8.0)
        base_tp = current_kpis.get("traffic_throughput", 4800)

        # Baseline trend leading up to current step
        steps = ["T-5m", "T-4m", "T-3m", "T-2m", "T-1m", "Live"]
        # Multipliers based on realistic fluctuation around baseline
        wait_series = [
            round(base_wait * 1.08, 1),
            round(base_wait * 1.04, 1),
            round(base_wait * 1.12, 1),
            round(base_wait * 0.98, 1),
            round(base_wait * 1.02, 1),
            round(base_wait, 1),
        ]
        queue_series = [
            round(base_queue * 1.15, 1),
            round(base_queue * 1.05, 1),
            round(base_queue * 1.10, 1),
            round(base_queue * 0.95, 1),
            round(base_queue * 1.00, 1),
            round(base_queue, 1),
        ]
        tp_series = [
            round(base_tp * 0.96),
            round(base_tp * 0.98),
            round(base_tp * 0.94),
            round(base_tp * 1.01),
            round(base_tp * 1.00),
            round(base_tp),
        ]
    else:
        steps = [d.get("time", f"T{i}") for i, d in enumerate(history_data)]
        wait_series = [d.get("avg_waiting_time", 0) for d in history_data]
        queue_series = [d.get("avg_queue_length", 0) for d in history_data]
        tp_series = [d.get("traffic_throughput", 0) for d in history_data]

    # Create figure with secondary y-axis for throughput
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Waiting time line
    fig.add_trace(
        go.Scatter(
            x=steps,
            y=wait_series,
            mode="lines+markers",
            name="Avg Delay (s)",
            line=dict(color=CYAN, width=2.5),
            marker=dict(size=6, color=CYAN),
            hovertemplate="%{x}: %{y:.1f} s<extra></extra>",
        ),
        secondary_y=False,
    )

    # Queue length line
    fig.add_trace(
        go.Scatter(
            x=steps,
            y=queue_series,
            mode="lines+markers",
            name="Avg Queue (veh)",
            line=dict(color=AMBER, width=2.5, dash="dash"),
            marker=dict(size=6, color=AMBER),
            hovertemplate="%{x}: %{y:.1f} veh<extra></extra>",
        ),
        secondary_y=False,
    )

    # Throughput line on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=steps,
            y=tp_series,
            mode="lines+markers",
            name="Throughput (veh/h)",
            line=dict(color=GREEN, width=2),
            marker=dict(size=5, color=GREEN),
            hovertemplate="%{x}: %{y:.0f} veh/h<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_xaxes(title_text="Time Window")
    fig.update_yaxes(title_text="Delay (s) / Queue (veh)", secondary_y=False)
    fig.update_yaxes(title_text="Throughput (veh/h)", secondary_y=True, showgrid=False)

    return _apply_dark_layout(fig, "Live Performance Trends (Delay, Queue & Throughput)", height=350)


def create_kpi_cards_html(kpis: Dict[str, Any]) -> str:
    """Generate HTML snippet rendering styled KPI metric cards."""
    cards = [
        {
            "label": "Avg Waiting Time",
            "value": f"{kpis.get('avg_waiting_time', 0)}",
            "unit": "sec / veh",
            "icon": "⏱️",
            "accent": CYAN,
        },
        {
            "label": "Average Queue",
            "value": f"{kpis.get('avg_queue_length', 0)}",
            "unit": f"veh ({kpis.get('total_queue_length', 0)} total)",
            "icon": "🚗",
            "accent": AMBER,
        },
        {
            "label": "Traffic Throughput",
            "value": f"{int(kpis.get('traffic_throughput', 0)):,}",
            "unit": "veh / hour",
            "icon": "⚡",
            "accent": GREEN,
        },
        {
            "label": "Fuel Consumption",
            "value": f"{kpis.get('fuel_consumption', 0)}",
            "unit": "Liters / hr",
            "icon": "⛽",
            "accent": PURPLE,
        },
        {
            "label": "CO₂ Emissions",
            "value": f"{kpis.get('co2_emissions', 0)}",
            "unit": "kg / hr",
            "icon": "🌱",
            "accent": "#10b981",
        },
        {
            "label": "Emergency Corridor",
            "value": f"{kpis.get('emergency_travel_time', 0)}",
            "unit": "sec (I1 → I6)",
            "icon": "🚑",
            "accent": RED,
        },
    ]

    cards_html = "".join(
        f"""
        <div style="
            background: rgba(14, 20, 34, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-left: 4px solid {c['accent']};
            border-radius: 10px;
            padding: 14px 16px;
            min-width: 155px;
            flex: 1;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af;">{c['label']}</span>
                <span style="font-size: 16px;">{c['icon']}</span>
            </div>
            <div style="font-size: 24px; font-weight: 700; color: #f9fafb; font-family: monospace;">{c['value']}</div>
            <div style="font-size: 11px; color: #6b7280; margin-top: 3px;">{c['unit']}</div>
        </div>
        """
        for c in cards
    )

    return f"""
    <div style="
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 22px;
        width: 100%;
    ">
        {cards_html}
    </div>
    """
