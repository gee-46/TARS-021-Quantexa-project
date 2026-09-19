"""KPI calculation module for traffic network state.

Calculates operational and environmental KPIs derived directly
from node and edge attributes in the NetworkX traffic graph.
"""

from typing import Dict, Any, List
import networkx as nx


def calculate_kpis(network: nx.Graph) -> Dict[str, Any]:
    """Calculate aggregate KPIs from the current network state.

    Parameters
    ----------
    network : nx.Graph
        The traffic network graph with intersection and road attributes.

    Returns
    -------
    dict
        Dictionary containing aggregate KPI values:
        - avg_waiting_time: Average delay per vehicle (seconds)
        - avg_queue_length: Average queue length across intersections (vehicles)
        - total_queue_length: Total queued vehicles across network
        - traffic_throughput: Estimated vehicle departures per hour (veh/h)
        - fuel_consumption: Estimated fuel consumed per hour (L/h)
        - co2_emissions: Estimated CO2 emissions per hour (kg/h)
        - emergency_travel_time: Estimated traversal time for corridor (seconds)
    """
    nodes = list(network.nodes(data=True))
    if not nodes:
        return {
            "avg_waiting_time": 0.0,
            "avg_queue_length": 0.0,
            "total_queue_length": 0,
            "traffic_throughput": 0.0,
            "fuel_consumption": 0.0,
            "co2_emissions": 0.0,
            "emergency_travel_time": 0.0,
        }

    total_queue = 0
    total_density = 0
    total_wait = 0.0
    total_throughput = 0.0

    for nid, data in nodes:
        q = data.get("queue_length", 0)
        density = data.get("traffic_density", 0)
        signal = str(data.get("signal_state", "red")).lower()
        green_dur = data.get("green_duration", 30)
        red_dur = data.get("red_duration", 30)
        cycle = green_dur + red_dur if (green_dur + red_dur) > 0 else 60

        total_queue += q
        total_density += density

        # Delay formula: queuing delay + signal phase penalty
        # Red phase adds average remaining red time (red_dur / 2), green adds clearance delay
        phase_penalty = (red_dur * 0.5) if signal == "red" else (red_dur * 0.15)
        node_wait = (q * 2.8) + phase_penalty
        total_wait += node_wait

        # Throughput estimation (vehicles per hour processed at intersection)
        # Saturation flow ~ 1600 veh/hr per lane, scaled by green ratio & density
        green_ratio = green_dur / cycle
        effective_capacity = 1600 * green_ratio
        # Demand factor
        demand_factor = min(1.2, density / 50.0)
        node_throughput = effective_capacity * demand_factor
        total_throughput += node_throughput

    num_nodes = len(nodes)
    avg_queue = total_queue / num_nodes
    avg_wait = total_wait / num_nodes

    # Fuel consumption estimation:
    # - Idling queue consumes ~0.7 Liters/hour per vehicle
    # - Moving traffic consumes ~0.06 Liters per km at urban speeds (~25 km/h -> 1.5 L/hr per veh)
    moving_vehicles = max(0, total_density - total_queue)
    fuel_idle = total_queue * 0.7
    fuel_moving = moving_vehicles * 0.06 * 25 * 0.1
    fuel_rate = round(fuel_idle + fuel_moving, 2)

    # CO2 emissions: 2.31 kg CO2 per liter of gasoline
    co2_rate = round(fuel_rate * 2.31, 2)

    # Emergency travel time along standard emergency corridor (I1 -> I2 -> I5 -> I6)
    # Free-flow time ~ 95s + queue and signal delays at corridor nodes
    corridor_nodes = ["I1", "I2", "I5", "I6"]
    corridor_delay = 0.0
    for cid in corridor_nodes:
        if network.has_node(cid):
            cdata = network.nodes[cid]
            if str(cdata.get("signal_state", "")).lower() == "red":
                corridor_delay += cdata.get("red_duration", 30) * 0.4
            corridor_delay += cdata.get("queue_length", 0) * 1.5
    emergency_time = round(95.0 + corridor_delay, 1)

    return {
        "avg_waiting_time": round(avg_wait, 1),
        "avg_queue_length": round(avg_queue, 1),
        "total_queue_length": int(total_queue),
        "traffic_throughput": round(total_throughput, 0),
        "fuel_consumption": fuel_rate,
        "co2_emissions": co2_rate,
        "emergency_travel_time": emergency_time,
    }


def get_intersection_data(network: nx.Graph) -> List[Dict[str, Any]]:
    """Extract tabular metrics for all intersections in the network."""
    rows = []
    for nid in sorted(network.nodes()):
        data = network.nodes[nid]
        rows.append({
            "intersection_id": nid,
            "traffic_density": data.get("traffic_density", 0),
            "queue_length": data.get("queue_length", 0),
            "signal_state": str(data.get("signal_state", "unknown")).upper(),
            "green_duration": data.get("green_duration", 30),
            "red_duration": data.get("red_duration", 30),
            "road_capacity": data.get("road_capacity", 100),
        })
    return rows
