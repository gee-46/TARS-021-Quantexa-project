// Presentation helpers that turn backend data into the node/edge objects the visual components draw.
// Nothing here invents traffic data: queues, waits and plans come from the Python simulator via api.js.
// Only the screen coordinates are presentation choices.

const LAYOUT = [
  { x: 150, y: 330 },
  { x: 400, y: 230 },
  { x: 650, y: 230 },
  { x: 860, y: 330 },
];

// Queue-load % is a display scale only: mean queue / reference vehicles (reference comes from the API).
export function queueLoadPercent(meanQueue, reference) {
  return Math.max(0, Math.min(100, Math.round((meanQueue / Math.max(1, reference)) * 100)));
}

// Same rule as the simulator's SignalState: green while (t mod cycle) < green duration.
export function signalAt(greenSeconds, cycleLength, t) {
  return t % cycleLength < greenSeconds ? 'GREEN' : 'RED';
}

export function congestionLabel(loadPercent) {
  if (loadPercent >= 85) return 'high';
  if (loadPercent >= 55) return 'medium';
  return 'low';
}

/**
 * Build the node map the visualizer/inspector expect.
 * metrics: simulator metrics for the run currently displayed; plan/bestPlan: {I1: 30, ...}.
 */
export function buildIntersections({ network, metrics, plan, bestPlan, clock }) {
  if (!network) return {};
  const ref = network.queue_reference_vehicles;
  const out = {};
  network.nodes.forEach((n, i) => {
    const pos = LAYOUT[i % LAYOUT.length];
    const meanQueue = metrics?.approach_mean_queue?.[n.id] ?? n.initial_queue;
    const load = queueLoadPercent(meanQueue, ref);
    const green = plan?.[n.id] ?? 30;
    const best = bestPlan?.[n.id];
    out[n.id] = {
      id: n.id,
      name: n.name,
      x: pos.x,
      y: pos.y,
      density: load,
      capacity: load,
      queue: Math.round(meanQueue),
      initialQueue: n.initial_queue,
      finalQueue: metrics?.final_queues?.[n.id],
      meanHeadWait: metrics?.approach_mean_head_wait?.[n.id],
      maxHeadWait: metrics?.approach_max_head_wait?.[n.id],
      signal: signalAt(green, network.cycle_length, clock),
      signalDuration: green,
      optimizedDuration: best,
      optimizedSignal: best === undefined ? undefined : 'GREEN',
      arrivalRate: n.arrival_rate,
      crossStreetRate: n.cross_street_rate,
      busProbability: n.bus_probability,
      connectedTo: network.edges.filter((e) => e.from === n.id || e.to === n.id).map((e) => (e.from === n.id ? e.to : e.from)),
      phase: `Green ${green} s of a ${network.cycle_length} s cycle`,
    };
  });
  return out;
}

export function buildRoads(network, intersections) {
  if (!network) return [];
  return network.edges.map((e) => {
    const from = intersections[e.from];
    return {
      id: e.id,
      from: e.from,
      to: e.to,
      name: `${e.from} → ${e.to}`,
      congestion: congestionLabel(from ? from.density : 0),
    };
  });
}

export function emergencyRoutes(network) {
  return (network?.ambulances || []).map((a) => ({ id: a.vehicle_id, priority: a.priority, route: a.route }));
}
