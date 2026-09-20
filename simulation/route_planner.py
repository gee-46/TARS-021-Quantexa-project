"""Queue-aware emergency route planning on the junction graph (NetworkX).

Given an origin and a destination junction, choose the route with the lowest expected travel time, where each hop costs

    hop_time(u -> v) + expected_queue_delay(v)
    expected_queue_delay(v) = queue_v * cycle / (service_rate * green_v)      [seconds]

i.e. the time the queue ahead of the ambulance at v needs to discharge through v's share of the signal cycle. The queues
come from the simulator's real per-junction queues, and the signal plan from the plan in force.

Scope notes (honest):
* The QuantumFlow network is one arterial (a path graph), so origin -> destination has exactly ONE simple path and the
  planner returns it. The planner itself is topology-agnostic (tested on a graph with a bypass), but the microscopic
  simulator only drives monotone routes along the arterial, so alternatives cannot be simulated end to end here.
* The expected delay is a planning ESTIMATE; response times reported alongside it come from the simulator.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx


@dataclass(frozen=True)
class RoutePlan:
    origin: str
    destination: str
    path: List[str]
    free_flow_seconds: float
    expected_queue_delay_seconds: float
    expected_total_seconds: float
    junction_delay: Dict[str, float]  # expected queue delay at each junction on the path (origin excluded)
    alternatives: List[Dict[str, Any]]  # other simple paths, cheapest first (empty when the route is unique)
    unique_path: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def expected_queue_delay(queue: float, green_seconds: float, cycle: float, service_rate: float = 1.0) -> float:
    """Seconds for a queue of ``queue`` vehicles to discharge given ``green_seconds`` of green per ``cycle``."""
    if queue <= 0:
        return 0.0
    return float(queue) * float(cycle) / (float(service_rate) * max(1.0, float(green_seconds)))


def build_graph(nodes: Sequence[str], edges: Optional[Iterable[Tuple[str, str]]] = None) -> nx.Graph:
    """Undirected junction graph; default edges chain the nodes in order (the arterial)."""
    g = nx.Graph()
    g.add_nodes_from(nodes)
    if edges is None:
        edges = list(zip(nodes[:-1], nodes[1:]))
    g.add_edges_from(edges)
    return g


def plan_route(
    graph: nx.Graph,
    origin: str,
    destination: str,
    queues: Dict[str, float],
    plan: Dict[str, int],
    cycle: float = 60.0,
    hop_seconds: float = 2.0,
    service_rate: float = 1.0,
    max_alternatives: int = 3,
) -> RoutePlan:
    """Cheapest path from origin to destination by hop time plus expected queue delay at each entered junction."""
    for n in (origin, destination):
        if n not in graph:
            raise ValueError(f"Unknown junction '{n}'.")
    if origin == destination:
        raise ValueError("Origin and destination must differ.")
    if not nx.has_path(graph, origin, destination):
        raise ValueError(f"No path from {origin} to {destination}.")

    delay = {n: expected_queue_delay(queues.get(n, 0.0), plan.get(n, 30), cycle, service_rate) for n in graph.nodes}

    def weight(u: str, v: str, _attrs: Dict[str, Any]) -> float:
        return hop_seconds + delay[v]

    def cost(path: Sequence[str]) -> Tuple[float, float]:
        hops = hop_seconds * (len(path) - 1)
        wait = sum(delay[n] for n in path[1:])
        return hops, wait

    best = nx.shortest_path(graph, origin, destination, weight=weight)
    hops, wait = cost(best)

    alts: List[Dict[str, Any]] = []
    for p in nx.shortest_simple_paths(graph, origin, destination, weight=weight):
        if list(p) == list(best):
            continue
        h, w = cost(p)
        alts.append({"path": list(p), "expected_total_seconds": h + w})
        if len(alts) >= max_alternatives:
            break

    return RoutePlan(
        origin=origin,
        destination=destination,
        path=list(best),
        free_flow_seconds=hops,
        expected_queue_delay_seconds=wait,
        expected_total_seconds=hops + wait,
        junction_delay={n: delay[n] for n in best[1:]},
        alternatives=alts,
        unique_path=len(alts) == 0,
    )
