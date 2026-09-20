import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import TrafficScene from '../components/TrafficScene';
import KpiCards from '../components/KpiCards';
import { useTraffic } from '../context/TrafficContext';
import { Panel, Note, Btn, fmt } from '../components/ui';
import { buildStoryModel, frameAt, frameLive, PHASE_TEXT, laneY } from '../services/storyModel';

const TONE = { info: 'var(--info)', warn: 'var(--amber)', red: 'var(--red)', green: 'var(--green)' };

function useStoryClock(total, active) {
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(true);
  useEffect(() => {
    if (!active || !playing || !total) return undefined;
    let raf;
    let prev = performance.now();
    const tick = (now) => {
      const dt = Math.min(0.1, (now - prev) / 1000);
      prev = now;
      setT((x) => (x + dt > total ? 0 : x + dt)); // loops so the story keeps explaining itself
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, playing, total]);
  return { t, setT, playing, setPlaying };
}

function Timeline({ model, t, seek }) {
  const { T } = model;
  const segs = [
    { key: 'before', label: 'BEFORE', sub: `Ambulance response ${fmt.n(model.respB, 0)} s`, a: 0, b: T.beforeEnd, color: 'var(--red)' },
    { key: 'opt', label: 'OPTIMISATION', sub: 'Corridor enabled, signals switch', a: T.beforeEnd, b: T.actEnd, color: 'var(--info)' },
    { key: 'after', label: 'AFTER', sub: `Ambulance response ${fmt.n(model.respA, 0)} s`, a: T.actEnd, b: T.afterEnd, color: 'var(--green)' },
  ];
  const span = T.afterEnd;
  const pos = Math.min(1, t / span) * 100;
  return (
    <div style={{ padding: '10px 14px 12px', borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
      <div style={{ position: 'relative', display: 'flex', gap: 3 }}>
        {segs.map((s) => {
          const on = t >= s.a && t < s.b + (s.key === 'after' ? 99 : 0);
          return (
            <button
              key={s.key}
              onClick={() => seek(s.a + 0.01)}
              style={{ flex: (s.b - s.a) / span, minWidth: 120, textAlign: 'left', cursor: 'pointer', fontFamily: 'inherit', background: on ? 'var(--surface-2)' : 'var(--surface)', border: '1px solid var(--border)', borderTop: `4px solid ${s.color}`, borderRadius: 4, padding: '6px 10px' }}
            >
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: s.color, letterSpacing: '0.06em' }}>{s.label}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>{s.sub}</div>
            </button>
          );
        })}
        <div style={{ position: 'absolute', left: `${pos}%`, top: -4, bottom: -4, width: 2, background: 'var(--charcoal)', pointerEvents: 'none' }} />
      </div>
    </div>
  );
}

function StatusRow({ k, v, tone }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '5px 0', borderBottom: '1px solid var(--surface-3)', fontSize: '0.82rem' }}>
      <span style={{ color: 'var(--muted)' }}>{k}</span>
      <strong style={{ color: tone ? TONE[tone] || tone : 'var(--text)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{v}</strong>
    </div>
  );
}

export default function LiveTrafficPage() {
  const ctx = useTraffic();
  const { network, story, baselineMetrics, metrics, currentPlan, baselinePlan, clock, emergencyCorridorActive, emergencyRoutes, hasAmbulances, optimizationResult, isOptimizing, handleRunOptimization, setStoryPhase, loading, scenarioId } = ctx;

  const model = useMemo(() => buildStoryModel({ network, story }), [network, story]);
  const { t, setT, playing, setPlaying } = useStoryClock(model?.T.total || 0, !!model);
  const names = useMemo(() => Object.fromEntries((network?.nodes || []).map((n) => [n.id, n.name])), [network]);
  const frame = model ? frameAt(model, t) : null;
  const phase = frame?.phase || null;

  const restartKey = useRef(scenarioId);
  useEffect(() => {
    if (restartKey.current !== scenarioId) {
      restartKey.current = scenarioId;
      setT(0);
    }
  }, [scenarioId, setT]);
  useEffect(() => {
    setStoryPhase(phase);
  }, [phase, setStoryPhase]);
  useEffect(() => () => setStoryPhase(null), [setStoryPhase]);

  if (!network) {
    return <Note tone={loading ? 'info' : 'error'}>{loading ? 'Loading the traffic network from the backend…' : 'No network data. Is the QuantumFlow API running (python -m uvicorn api_server:app --port 8000)?'}</Note>;
  }

  // ---- scene props: animated story when available, otherwise the live static network
  let scene;
  let sceneMeta = null;
  if (model && frame) {
    const ambulances = frame.amb
      ? [{ id: model.amb.vehicle_id, x: frame.amb.x, y: laneY(model.dir), dir: model.dir, label: model.amb.vehicle_id, stuck: frame.amb.state === 'stuck' }]
      : [];
    const tones = {};
    const labels = {};
    model.ids.forEach((id) => {
      if (!frame.showRealQueue) return;
      const q = frame.realQueue[id];
      labels[id] = `Queue ${Math.round(q)} veh`;
      tones[id] = frame.corridor && model.route.includes(id) ? 'green' : q / network.queue_reference_vehicles > 0.55 ? 'red' : undefined;
    });
    scene = (
      <TrafficScene
        ids={model.ids} xs={model.xs} names={names} signals={frame.signals} cars={frame.cars} ambulances={ambulances}
        routes={[{ id: model.amb.vehicle_id, route: model.route, dir: model.dir }]} corridor={frame.corridor}
        queueLabels={labels} queueTones={tones} unit={model.unit} ariaLabel="Animated traffic scenario with an ambulance"
      />
    );
  } else {
    const live = frameLive({ network, metrics, plan: currentPlan, clock, corridorActive: emergencyCorridorActive, routes: emergencyRoutes });
    const labels = {};
    live.ids.forEach((id) => { labels[id] = `Queue ${Math.round(live.queues[id])} veh`; });
    scene = (
      <TrafficScene
        ids={live.ids} xs={live.xs} names={names} signals={live.signals} cars={live.cars}
        ambulances={live.ambs.map((a) => ({ id: a.id, x: a.x, y: a.y, dir: a.dir, label: a.id }))}
        routes={live.routes.map((r) => ({ id: r.id, route: r.route, dir: live.xs[r.route[r.route.length - 1]] >= live.xs[r.route[0]] ? 1 : -1 }))}
        corridor={emergencyCorridorActive} queueLabels={labels} unit={live.unit} ariaLabel="Traffic network"
      />
    );
    sceneMeta = story.status === 'loading' ? 'Loading the ambulance scenario from the backend…' : story.status === 'error' ? `Ambulance scenario unavailable: ${story.error}` : !hasAmbulances ? 'This scenario has no emergency vehicle, so there is no ambulance story. Pick scenario D, E, F or a Belagavi-inspired two-ambulance scenario in the header.' : null;
  }

  // ---- numbers for the panels (all from the backend run shown)
  const runMetrics = phase && ['activating', 'clearing', 'done'].includes(phase) ? story.data?.with_corridor : story.data?.without_corridor || metrics;
  const shown = runMetrics || baselineMetrics;
  const queueVals = network.nodes.map((n) => shown?.approach_mean_queue?.[n.id] ?? 0);
  const avgQueue = queueVals.reduce((a, b) => a + b, 0) / Math.max(1, queueVals.length);
  const load = Math.min(100, Math.round((avgQueue / network.queue_reference_vehicles) * 100));
  const phaseInfo = phase ? PHASE_TEXT[phase] : null;
  const ambStatus = { normal: ['APPROACHING', 'info'], congestion: ['APPROACHING', 'warn'], stuck: ['DELAYED', 'red'], activating: ['CORRIDOR ENABLED', 'info'], clearing: ['MOVING', 'green'], done: ['CLEARED', 'green'] }[phase] || ['NO EMERGENCY', null];
  const arb = story.data?.conflict_arbiter;
  const winner = arb ? arb.records[arb.winner] : null;
  const activeSignals = frame?.signals || frameLive({ network, metrics, plan: currentPlan, clock, corridorActive: false, routes: [] }).signals;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 330px', gap: 14, alignItems: 'start' }} className="live-grid">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
        <section style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden', background: 'var(--surface)' }}>
          {/* stage banner */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '8px 14px', background: 'var(--charcoal)', color: '#fff', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: phaseInfo ? TONE[phaseInfo.tone] : '#9aa4af', boxShadow: '0 0 0 3px rgba(255,255,255,0.15)' }} />
              <strong style={{ fontSize: '0.86rem', letterSpacing: '0.03em' }}>{phaseInfo ? `${phaseInfo.n}. ${phaseInfo.title}` : 'LIVE TRAFFIC'}</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.78rem', color: '#d7dce1' }}>
              {model && frame?.runInfo && <span style={{ fontVariantNumeric: 'tabular-nums' }}>{model.amb.vehicle_id} elapsed: <strong style={{ color: '#fff' }}>{fmt.n(frame.elapsed, 0)} s</strong> {frame.runInfo === 'before' ? `of ${fmt.n(model.respB, 0)} s` : `of ${fmt.n(model.respA, 0)} s`}</span>}
              {model && phase === 'done' && <strong style={{ color: '#7be0a0' }}>Response {fmt.n(model.respB, 0)} s → {fmt.n(model.respA, 0)} s</strong>}
              {model && (
                <span style={{ display: 'inline-flex', gap: 6 }}>
                  <button aria-label={playing ? 'Pause' : 'Play'} onClick={() => setPlaying(!playing)} style={ctl}>{playing ? <Pause size={14} /> : <Play size={14} />}</button>
                  <button aria-label="Restart" onClick={() => { setT(0); setPlaying(true); }} style={ctl}><RotateCcw size={14} /></button>
                </span>
              )}
            </div>
          </div>
          {scene}
          {model ? (
            <Timeline model={model} t={t} seek={setT} />
          ) : (
            sceneMeta && <div style={{ padding: '10px 14px' }}><Note tone={story.status === 'error' ? 'error' : 'info'}>{sceneMeta}</Note></div>
          )}
        </section>
        {model && (
          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', lineHeight: 1.5 }}>
            Replay of the backend simulation for {network.title} (seed {ctx.seed}). Queue lengths, signal plan, and the ambulance's response and waiting times with and without the corridor are the simulator's values;
            only the time scale is compressed (1 s on screen ≈ {fmt.n(1 / model.k, 0)} simulated s). Vehicle icons and positions are schematic{model.unit > 1 ? ` (1 icon = ${model.unit} vehicles)` : ''}.
            {model.horizonNote ? ` Note: ${model.horizonNote}.` : ''}
          </div>
        )}
        <KpiCards />
      </div>

      {/* operational panels */}
      <aside style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Panel title="Traffic status">
          <div>
            <StatusRow k="Vehicles in simulation" v={fmt.int(shown?.vehicles_generated)} />
            <StatusRow k="Active junctions" v={network.nodes.length} />
            <StatusRow k="Average queue" v={`${fmt.n(avgQueue, 1)} veh`} tone={load > 55 ? 'red' : undefined} />
            <StatusRow k={`Network load (scale ${network.queue_reference_vehicles} veh)`} v={`${load}%`} tone={load > 85 ? 'red' : load > 55 ? 'warn' : 'green'} />
          </div>
        </Panel>

        <Panel title="Emergency response">
          {model ? (
            <div>
              <StatusRow k="Vehicle" v={`${model.amb.vehicle_id} (priority ${model.amb.priority})`} />
              <StatusRow k="Status" v={ambStatus[0]} tone={ambStatus[1]} />
              <StatusRow k="Route" v={model.route.join(' → ')} />
              <StatusRow k="Response, no corridor" v={`${fmt.n(model.respB, 0)} s`} tone="red" />
              <StatusRow k="Response, corridor" v={`${fmt.n(model.respA, 0)} s`} tone="green" />
              <StatusRow k="Time saved" v={`${fmt.n(model.respB - model.respA, 0)} s`} />
              {winner && <StatusRow k={`Conflict at ${arb.conflict_intersection}`} v={`${winner.sequence.join(' → ')} (QUBO)`} />}
            </div>
          ) : (
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{hasAmbulances ? 'Waiting for the ambulance scenario…' : 'No emergency vehicle in this scenario.'}</div>
          )}
        </Panel>

        <Panel title="Signal control">
          <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
            <tbody>
              {network.nodes.map((n) => {
                const s = activeSignals[n.id];
                const green = (frame ? model.plan : currentPlan || baselinePlan)?.[n.id];
                return (
                  <tr key={n.id} style={{ borderBottom: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '5px 0', fontWeight: 700 }}>{n.id}</td>
                    <td style={{ padding: '5px 0' }}>
                      <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: '50%', marginRight: 6, background: s?.main ? 'var(--green)' : 'var(--red)' }} />
                      <strong style={{ color: s?.main ? 'var(--green)' : 'var(--red)' }}>{s?.main ? 'GREEN' : 'RED'}</strong>
                      {s?.forced && <span style={{ color: 'var(--green)', fontSize: '0.68rem' }}> · corridor</span>}
                    </td>
                    <td style={{ padding: '5px 0', textAlign: 'right', color: 'var(--muted)' }}>{green} s green</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>

        <Panel title="Optimisation">
          <div>
            <StatusRow k="Optimisation" v={phase && ['activating', 'clearing', 'done'].includes(phase) ? 'ACTIVE' : 'STANDBY'} tone={phase && ['activating', 'clearing', 'done'].includes(phase) ? 'green' : undefined} />
            <StatusRow k="Emergency corridor" v={phase && ['activating', 'clearing', 'done'].includes(phase) ? 'ENABLED' : hasAmbulances ? 'READY' : 'N/A'} tone={phase && ['activating', 'clearing', 'done'].includes(phase) ? 'green' : undefined} />
            {optimizationResult && <StatusRow k="QUBO best solver" v={optimizationResult.best_solver.toUpperCase()} />}
          </div>
          {optimizationResult && <div style={{ fontSize: '0.74rem', color: 'var(--text-2)', lineHeight: 1.45 }}>{optimizationResult.verdict}</div>}
          <div><Btn onClick={handleRunOptimization} disabled={isOptimizing} tone="ghost">{isOptimizing ? 'Solving…' : 'Run QUBO signal optimisation'}</Btn></div>
        </Panel>
      </aside>
    </div>
  );
}

const ctl = { background: 'transparent', border: '1px solid rgba(255,255,255,0.35)', color: '#fff', borderRadius: 4, width: 28, height: 24, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' };

