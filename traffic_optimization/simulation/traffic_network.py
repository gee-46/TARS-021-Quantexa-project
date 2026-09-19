"""Authoritative 4-Intersection Arterial Network Graph (I1 -> I2 -> I3 -> I4).

Provides `get_traffic_network()` that constructs a NetworkX graph for the
canonical 4-intersection linear arterial corridor, strictly matching the
authoritative QuantumFlow backend specification.
"""

from typing import Dict, Any, Optional
import networkx as nx

INTERSECTIONS = ("I1", "I2", "I3", "I4")

# Arterial corridor coordinates (spaced evenly along an arterial corridor)
# Centered in an illustrative urban corridor layout
NODE_COORDINATES = {
    "I1": (12.9716, 77.5946),  # Intersection 1 (Entrance West)
    "I2": (12.9716, 77.6046),  # Intersection 2 (Corridor Junction)
    "I3": (12.9716, 77.6146),  # Intersection 3 (Corridor Junction)
    "I4": (12.9716, 77.6246),  # Intersection 4 (Exit East)
}


def get_traffic_network(
    queues: Optional[Dict[str, float]] = None,
    signal_plan: Optional[Dict[str, int]] = None,
    signal_states: Optional[Dict[str, str]] = None,
) -> nx.Graph:
    """Create and return the authoritative 4-intersection traffic network graph.

    Parameters
    ----------
    queues : dict, optional
        Observed queue counts per intersection {"I1": 10, ...}.
    signal_plan : dict, optional
        Green phase durations {"I1": 45, ...}.
    signal_states : dict, optional
        Active signal status {"I1": "GREEN" / "NORMAL", ...}.

    Returns
    -------
    nx.Graph
        4-node arterial graph with authoritative attributes.
    """
    G = nx.Graph()

    default_queues = {"I1": 10, "I2": 15, "I3": 8, "I4": 12}
    default_plan = {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
    default_states = {"I1": "GREEN", "I2": "RED", "I3": "GREEN", "I4": "RED"}

    active_queues = queues if queues is not None else default_queues
    active_plan = signal_plan if signal_plan is not None else default_plan
    active_states = signal_states if signal_states is not None else default_states

    for inter in INTERSECTIONS:
        lat, lng = NODE_COORDINATES[inter]
        q = float(active_queues.get(inter, 0.0))
        dur = int(active_plan.get(inter, 30))
        sig = str(active_states.get(inter, "NORMAL")).upper()
        # Density ratio based on nominal queue capacity (20 veh)
        density_pct = min(100, int((q / 20.0) * 100))

        G.add_node(
            inter,
            intersection_id=inter,
            latitude=lat,
            longitude=lng,
            traffic_density=density_pct,
            queue_length=int(q),
            road_capacity=100,
            signal_state="green" if ("GREEN" in sig or sig == "NORMAL") else "red",
            green_duration=dur,
            red_duration=60 - dur,
        )

    # Directed arterial connections: I1 -> I2 -> I3 -> I4
    edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
    for idx, (src, dst) in enumerate(edges, start=1):
        G.add_edge(
            src,
            dst,
            road_id=f"Arterial_Seg_{idx}",
            source=src,
            destination=dst,
            capacity=100,
            traffic_volume=int(active_queues.get(src, 0.0)),
            status="open",
        )

    return G
