"""Folium map rendering for the traffic network.

Provides `render_map(network: nx.Graph) -> folium.Map` which draws:
- Intersections as circle markers (green/red based on signal_state)
- Roads as polylines (color based on traffic_volume / capacity)
"""

import folium
import networkx as nx

def _signal_color(state: str) -> str:
    return {
        "green": "#4edea3",
        "red": "#ef4444",
        "yellow": "#ffd700",
    }.get(state.lower(), "#8b9cb0")

def render_map(network: nx.Graph) -> folium.Map:
    """Render the traffic network onto a Folium map.

    Parameters
    ----------
    network : nx.Graph
        Graph with node attributes (latitude, longitude, signal_state, etc.)
        and edge attributes (traffic_volume, capacity).
    Returns
    -------
    folium.Map
        Folium map object ready to be displayed in Streamlit.
    """
    # Determine map centre – average of all node coordinates
    lats = [data["latitude"] for _, data in network.nodes(data=True)]
    lngs = [data["longitude"] for _, data in network.nodes(data=True)]
    centre = [sum(lats) / len(lats), sum(lngs) / len(lngs)]

    m = folium.Map(location=centre, zoom_start=14, tiles="OpenStreetMap")

    # Draw edges (roads)
    for u, v, data in network.edges(data=True):
        src = network.nodes[u]
        dst = network.nodes[v]
        # Simple colour based on traffic volume proportion
        volume = data.get("traffic_volume", 0)
        capacity = data.get("capacity", 1)
        intensity = min(1.0, volume / capacity)
        # Interpolate red (high) to green (low)
        line_color = "#ef4444" if intensity > 0.7 else "#4edea3"
        folium.PolyLine(
            locations=[(src["latitude"], src["longitude"]), (dst["latitude"], dst["longitude"])],
            color=line_color,
            weight=5,
            opacity=0.7,
            tooltip=f"{data.get('road_id')} ({volume}/{capacity})",
        ).add_to(m)

    # Draw nodes (intersections)
    for nid, data in network.nodes(data=True):
        folium.CircleMarker(
            location=(data["latitude"], data["longitude"]),
            radius=8,
            color=_signal_color(data.get("signal_state", "")),
            fill=True,
            fill_color=_signal_color(data.get("signal_state", "")),
            fill_opacity=0.9,
            tooltip=(
                f"{nid}<br>Density: {data.get('traffic_density')}<br>Queue: {data.get('queue_length')}"
            ),
        ).add_to(m)

    return m

def render_map_html(network: nx.Graph) -> str:
    """Return the HTML representation of the map for embedding in Streamlit components."""
    m = render_map(network)
    return m.get_root().render()
