// Story model: turns REAL backend numbers into a replayable traffic scene.
//
// Data used (all from the API, none invented):
//   * per-junction mean queues            -> queue lengths drawn as vehicle icons
//   * the fixed-time signal plan + cycle  -> signal heads (same cyclic rule as the simulator)
//   * ambulance response / waiting times, with and without the emergency corridor
//   * the ambulance route from the scenario configuration
// Presentation-only choices (frontend visualisation logic, labelled on screen):
//   * time compression (simulated seconds -> screen seconds)
//   * one vehicle icon = `unit` real vehicles when queues are long
//   * icon positions / colours

export const SCENE = { W: 1000, H: 430, roadY: 215, half: 26, carLen: 20, spacing: 25, cap: 12 };

export const junctionX = (i, n) => 170 + (n > 1 ? i * ((SCENE.W - 340) / (n - 1)) : 0);
export const laneY = (dir) => SCENE.roadY + (dir > 0 ? 13 : -13);

const ease = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
const lerp = (a, b, x) => a + (b - a) * x;

// screen-time budget of each story phase (seconds)
export const STORY_T = { normal: 1.3, congestion: 1.4, before: 5.5, activate: 1.7, hold: 3.5 };

function queuesOf(metrics, ids) {
  const q = metrics?.approach_mean_queue || {};
  return Object.fromEntries(ids.map((i) => [i, Math.max(0, q[i] ?? 0)]));
}

function iconCount(q, unit) {
  return q < 0.5 ? 0 : Math.min(SCENE.cap, Math.max(1, Math.ceil(q / unit)));
}

/** Ambulance keyframes for one run (before / after), in SIMULATED seconds. */
function ambulanceRun({ xs, route, dir, respTotal, waitTotal, queues, unit }) {
  const laneCount = (id) => Math.ceil(iconCount(queues[id], unit) / 2);
  const stop = (id) => xs[id] - dir * SCENE.half - dir * 4;
  const exit = (id) => xs[id] + dir * (SCENE.half + 8);
  const start = stop(route[0]) - dir * 120;

  const segs = [];
  let prev = start;
  route.forEach((id) => {
    const tailRaw = stop(id) - dir * laneCount(id) * SCENE.spacing;
    const tail = dir * (tailRaw - prev) < 0 ? prev : tailRaw; // never go backwards
    segs.push({ kind: 'travel', x0: prev, x1: tail, id });
    segs.push({ kind: 'wait', x0: tail, x1: stop(id), id, w: queues[id] + 0.5 });
    segs.push({ kind: 'pass', x0: stop(id), x1: exit(id), id });
    prev = exit(id);
  });

  const moveTotal = Math.max(0.1, respTotal - Math.max(0, waitTotal));
  const waitSum = segs.filter((s) => s.kind === 'wait').reduce((a, s) => a + s.w, 0) || 1;
  const moveDist = segs.filter((s) => s.kind !== 'wait').reduce((a, s) => a + Math.abs(s.x1 - s.x0), 0) || 1;
  let t = 0;
  const keys = segs.map((s) => {
    const dur = s.kind === 'wait' ? (Math.max(0, waitTotal) * s.w) / waitSum : (moveTotal * Math.abs(s.x1 - s.x0)) / moveDist;
    const k = { ...s, t0: t, t1: t + dur };
    t += dur;
    return k;
  });
  return { keys, total: t, start, end: prev };
}

function ambulanceAt(run, tSim) {
  const { keys } = run;
  if (tSim <= 0) return { x: run.start, state: 'waiting-start', seg: null };
  for (const k of keys) {
    if (tSim <= k.t1 + 1e-9) {
      const f = k.t1 > k.t0 ? (tSim - k.t0) / (k.t1 - k.t0) : 1;
      return { x: lerp(k.x0, k.x1, f), state: k.kind === 'wait' ? 'stuck' : 'moving', seg: k };
    }
  }
  return { x: run.end, state: 'done', seg: null };
}

/**
 * Build the replay model, or null when the scenario has no ambulance / data is missing.
 */
export function buildStoryModel({ network, story }) {
  if (!network || !story || story.status !== 'ready') return null;
  const data = story.data;
  const amb = [...network.ambulances].sort((a, b) => a.priority - b.priority)[0];
  if (!amb) return null;
  const ids = network.nodes.map((n) => n.id);
  const n = ids.length;
  const xs = Object.fromEntries(ids.map((id, i) => [id, junctionX(i, n)]));
  const route = amb.route.filter((id) => ids.includes(id));
  const dir = xs[route[route.length - 1]] >= xs[route[0]] ? 1 : -1;

  const rb = data.without_corridor.emergency_vehicle_results.find((v) => v.vehicle_id === amb.vehicle_id);
  const ra = data.with_corridor.emergency_vehicle_results.find((v) => v.vehicle_id === amb.vehicle_id);
  if (!rb || !ra) return null;
  const horizon = network.duration_seconds;
  const respB = rb.response_time ?? horizon;
  const respA = ra.response_time ?? horizon;

  const qB = queuesOf(data.without_corridor, ids);
  const qA = queuesOf(data.with_corridor, ids);
  const maxQ = Math.max(1, ...Object.values(qB), ...Object.values(qA));
  const unit = Math.max(1, Math.ceil(maxQ / SCENE.cap));

  const k = STORY_T.before / Math.max(1, respB); // screen seconds per simulated second
  const runB = ambulanceRun({ xs, route, dir, respTotal: respB, waitTotal: rb.waiting_time ?? 0, queues: qB, unit });
  const runA = ambulanceRun({ xs, route, dir, respTotal: respA, waitTotal: ra.waiting_time ?? 0, queues: qA, unit });
  const durAfter = Math.max(2.4, respA * k);

  const T = {
    normalEnd: STORY_T.normal,
    congEnd: STORY_T.normal + STORY_T.congestion,
    beforeEnd: STORY_T.normal + STORY_T.congestion + STORY_T.before,
  };
  T.actEnd = T.beforeEnd + STORY_T.activate;
  T.afterEnd = T.actEnd + durAfter;
  T.total = T.afterEnd + STORY_T.hold;

  return {
    ids, xs, route, dir, unit, k, T, qB, qA, respB, respA,
    waitB: rb.waiting_time ?? 0, waitA: ra.waiting_time ?? 0,
    runB, runA, amb, plan: data.plan, cycle: network.cycle_length,
    conflict: data.conflict_arbiter || null,
    horizonNote: rb.response_time === null ? 'ambulance did not finish without the corridor (shown as the simulation horizon)' : null,
  };
}

export function phaseAt(model, t) {
  const T = model.T;
  if (t < T.normalEnd) return 'normal';
  if (t < T.congEnd) return 'congestion';
  if (t < T.beforeEnd) return 'stuck';
  if (t < T.actEnd) return 'activating';
  if (t < T.afterEnd) return 'clearing';
  return 'done';
}

export const PHASE_TEXT = {
  normal: { n: 1, title: 'Normal traffic', tone: 'info' },
  congestion: { n: 2, title: 'Congestion builds at the junctions', tone: 'warn' },
  stuck: { n: 3, title: 'Ambulance stuck in the queue', tone: 'red' },
  activating: { n: 4, title: 'Optimisation active: emergency corridor enabled', tone: 'info' },
  clearing: { n: 5, title: 'Corridor clears: ambulance moving', tone: 'green' },
  done: { n: 6, title: 'Emergency response complete', tone: 'green' },
};

/** Everything the scene needs to draw at story time t (screen seconds). */
export function frameAt(model, t) {
  const { ids, xs, dir, T, k, route, plan, cycle } = model;
  const phase = phaseAt(model, t);
  const corridor = phase === 'activating' || phase === 'clearing' || phase === 'done';

  // queue level factor per junction: builds up, holds, then drops to the corridor run's real level
  const build = ease(t / T.congEnd);
  const drop = ease((t - T.beforeEnd) / (T.actEnd - T.beforeEnd + 0.6));
  const queues = {};
  ids.forEach((id) => {
    queues[id] = t < T.beforeEnd ? model.qB[id] * build : lerp(model.qB[id], model.qA[id], drop);
  });
  const showRealQueue = t >= T.congEnd;
  const realQueue = t < T.beforeEnd ? model.qB : model.qA;

  // ambulance
  let amb = null;
  let elapsed = 0;
  let runInfo = null;
  if (phase === 'normal') {
    amb = null;
  } else if (phase === 'congestion') {
    amb = { x: model.runB.start, state: 'arriving' };
  } else if (phase === 'stuck') {
    const ts = (t - T.congEnd) / k;
    amb = ambulanceAt(model.runB, ts);
    elapsed = Math.min(ts, model.runB.total);
    runInfo = 'before';
  } else if (phase === 'activating') {
    amb = { x: model.runA.start, state: 'waiting-start' };
  } else {
    const ts = (t - T.actEnd) / k;
    amb = ambulanceAt(model.runA, ts);
    elapsed = Math.min(ts, model.runA.total);
    runInfo = 'after';
  }
  if (amb && phase === 'done') amb.state = 'done';

  // signals: same cyclic rule as the simulator; route junctions forced green while the corridor is active
  const tauSim = t / k;
  const signals = {};
  ids.forEach((id) => {
    const cyc = tauSim % cycle < (plan[id] ?? 30);
    let forced = false;
    if (corridor && route.includes(id)) {
      const passed = amb && phase !== 'activating' && dir * (amb.x - (xs[id] + dir * (SCENE.half + 8))) > 24;
      forced = !passed;
    }
    signals[id] = { main: forced ? true : cyc, forced };
  });

  // queue cars per junction/lane (icons), skipping cars the ambulance has already overtaken
  const cars = [];
  ids.forEach((id) => {
    const iconsTotal = queues[id] < 0.5 ? 0 : Math.min(SCENE.cap, Math.max(1, Math.round(queues[id] / model.unit)));
    [1, -1].forEach((d) => {
      const nLane = Math.ceil(iconsTotal / 2);
      for (let i = 0; i < nLane; i++) {
        const x = xs[id] - d * (SCENE.half + 4) - d * (i * SCENE.spacing + SCENE.carLen / 2 + 3);
        if (amb && d === dir && dir * (x - amb.x) < 10 && phase !== 'normal' && phase !== 'congestion' && phase !== 'activating') continue;
        cars.push({ key: `${id}-${d}-${i}`, x, y: laneY(d), d, i });
      }
    });
  });

  return { phase, corridor, queues, showRealQueue, realQueue, amb, elapsed, runInfo, signals, cars };
}

/** Static frame for pages that just show the current network state (no story). */
export function frameLive({ network, metrics, plan, clock, corridorActive, routes }) {
  if (!network) return null;
  const ids = network.nodes.map((n) => n.id);
  const n = ids.length;
  const xs = Object.fromEntries(ids.map((id, i) => [id, junctionX(i, n)]));
  const q = queuesOf(metrics, ids);
  const maxQ = Math.max(1, ...Object.values(q));
  const unit = Math.max(1, Math.ceil(maxQ / SCENE.cap));
  const signals = {};
  const onRoute = new Set(corridorActive ? routes.flatMap((r) => r.route) : []);
  ids.forEach((id) => {
    const cyc = clock % network.cycle_length < (plan?.[id] ?? 30);
    signals[id] = { main: onRoute.has(id) ? true : cyc, forced: onRoute.has(id) };
  });
  const cars = [];
  ids.forEach((id) => {
    const icons = q[id] < 0.5 ? 0 : Math.min(SCENE.cap, Math.max(1, Math.ceil(q[id] / unit)));
    [1, -1].forEach((d) => {
      for (let i = 0; i < Math.ceil(icons / 2); i++) {
        cars.push({ key: `${id}-${d}-${i}`, x: xs[id] - d * (SCENE.half + 4) - d * (i * SCENE.spacing + SCENE.carLen / 2 + 3), y: laneY(d), d, i });
      }
    });
  });
  // ambulances parked at their origin (no animation on these pages)
  const ambs = (network.ambulances || []).map((a) => {
    const route = a.route.filter((id) => ids.includes(id));
    const d = xs[route[route.length - 1]] >= xs[route[0]] ? 1 : -1;
    return { id: a.vehicle_id, route, dir: d, x: xs[route[0]] - d * (SCENE.half + 4 + 92), y: laneY(d) };
  });
  return { ids, xs, unit, queues: q, signals, cars, ambs, corridor: corridorActive, routes };
}
