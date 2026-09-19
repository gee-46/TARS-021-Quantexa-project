"""Traffic network definition using NetworkX.

Provides a function `get_traffic_network()` that returns a graph with six
intersections (I1‑I6) and the connecting roads. Each node and edge stores the
attributes required for the later visualisation.
"""

import networkx as nx


def get_traffic_network() -> nx.Graph:
    """Create and return the traffic network graph.

    Returns
    -------
    nx.Graph
        Graph with node attributes:
        - intersection_id, latitude, longitude, traffic_density, queue_length,
          road_capacity, signal_state, green_duration, red_duration
        Edge attributes:
        - road_id, source, destination, capacity, traffic_volume, status
    """
    G = nx.Graph()

    # Example coordinates – a simple grid representing the diagram
    nodes = {
        "I1": {
            "intersection_id": "I1",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "traffic_density": 20,
            "queue_length": 5,
            "road_capacity": 100,
            "signal_state": "green",
            "green_duration": 30,
            "red_duration": 30,
        },
        "I2": {
            "intersection_id": "I2",
            "latitude": 37.7749,
            "longitude": -122.4144,
            "traffic_density": 40,
            "queue_length": 10,
            "road_capacity": 100,
            "signal_state": "red",
            "green_duration": 30,
            "red_duration": 30,
        },
        "I3": {
            "intersection_id": "I3",
            "latitude": 37.7749,
            "longitude": -122.4094,
            "traffic_density": 30,
            "queue_length": 7,
            "road_capacity": 100,
            "signal_state": "green",
            "green_duration": 30,
            "red_duration": 30,
        },
        "I4": {
            "intersection_id": "I4",
            "latitude": 37.7699,
            "longitude": -122.4194,
            "traffic_density": 25,
            "queue_length": 6,
            "road_capacity": 100,
            "signal_state": "red",
            "green_duration": 30,
            "red_duration": 30,
        },
        "I5": {
            "intersection_id": "I5",
            "latitude": 37.7699,
            "longitude": -122.4144,
            "traffic_density": 35,
            "queue_length": 8,
            "road_capacity": 100,
            "signal_state": "green",
            "green_duration": 30,
            "red_duration": 30,
        },
        "I6": {
            "intersection_id": "I6",
            "latitude": 37.7699,
            "longitude": -122.4094,
            "traffic_density": 45,
            "queue_length": 12,
            "road_capacity": 100,
            "signal_state": "red",
            "green_duration": 30,
            "red_duration": 30,
        },
    }

    for nid, attrs in nodes.items():
        G.add_node(nid, **attrs)

    # Roads according to the diagram
    edges = [
        ("I1", "I2"),
        ("I2", "I3"),
        ("I4", "I5"),
        ("I5", "I6"),
        ("I1", "I4"),
        ("I2", "I5"),
        ("I3", "I6"),
    ]

    for idx, (src, dst) in enumerate(edges, start=1):
        G.add_edge(
            src,
            dst,
            road_id=f"R{idx}",
            source=src,
            destination=dst,
            capacity=100,
            traffic_volume=0,
            status="open",
        )

    return G
