"""Folium map rendering for the authoritative 4-intersection arterial network (I1 -> I2 -> I3 -> I4).

Renders:
- 4 Intersections as styled circular nodes (color based on signal state)
- Connecting arterial corridor links with volume and capacity tooltips
- Clean illustrative centering for arterial corridor
"""

import folium
import networkx as nx


def _signal_color(state: str) -> str:
    """Return hex color for signal state."""
    st_clean = str(state).lower()
    if "green" in st_clean or st_clean == "normal":
        return "#4edea3"
    elif "red" in st_clean:
        return "#ef4444"
    elif "yellow" in st_clean:
        return "#ffd700"
    return "#38bdf8"


def render_map(network: nx.Graph) -> folium.Map:
    """Render the 4-intersection arterial network onto a Folium map.

    Parameters
    ----------
    network : nx.Graph
        Graph with node attributes (latitude, longitude, signal_state, etc.)
        and edge attributes (traffic_volume, capacity).

    Returns
    -------
    folium.Map
        Folium map object.
    """
    lats = [data["latitude"] for _, data in network.nodes(data=True)]
    lngs = [data["longitude"] for _, data in network.nodes(data=True)]
    centre = [sum(lats) / len(lats), sum(lngs) / len(lngs)] if lats else [12.9716, 77.6096]

    m = folium.Map(
        location=centre,
        zoom_start=14,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # Draw Arterial Roads
    for u, v, data in network.edges(data=True):
        src = network.nodes[u]
        dst = network.nodes[v]
        volume = data.get("traffic_volume", 0)
        capacity = data.get("capacity", 100)
        intensity = min(1.0, float(volume) / max(1.0, float(capacity)))

        line_color = "#ef4444" if intensity > 0.6 else ("#f59e0b" if intensity > 0.3 else "#38bdf8")

        folium.PolyLine(
            locations=[(src["latitude"], src["longitude"]), (dst["latitude"], dst["longitude"])],
            color=line_color,
            weight=6,
            opacity=0.85,
            tooltip=f"<b>{data.get('road_id', 'Arterial Segment')}</b><br>Flow Volume: {volume} veh | Capacity: {capacity} veh",
        ).add_to(m)

    # Draw Intersections (I1 to I4)
    for nid, data in network.nodes(data=True):
        sig = data.get("signal_state", "green")
        q = data.get("queue_length", 0)
        dur = data.get("green_duration", 30)
        dens = data.get("traffic_density", 0)

        folium.CircleMarker(
            location=(data["latitude"], data["longitude"]),
            radius=12,
            color="#ffffff",
            weight=2,
            fill=True,
            fill_color=_signal_color(sig),
            fill_opacity=0.95,
            tooltip=(
                f"<b>Intersection {nid}</b><br>"
                f"Active Signal: {str(sig).upper()}<br>"
                f"Green Phase: {dur}s / 60s<br>"
                f"Live Queue: {q} veh<br>"
                f"Density: {dens}%"
            ),
        ).add_to(m)

        # Add text label marker above node
        folium.Marker(
            location=(data["latitude"] + 0.0015, data["longitude"]),
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12px; font-weight: 700; color: #38bdf8; font-family: monospace; background: rgba(7, 9, 19, 0.85); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.4);">{nid}</div>'
            ),
        ).add_to(m)

    return m
