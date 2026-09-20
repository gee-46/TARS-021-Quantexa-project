import React, { useState } from 'react';
import { BarChart3, Scale, Timer } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { getPareto, runAdaptive } from '../services/api';
import { PageHeader, Panel, DataTable, Note, Btn, Stat, StatGrid, fmt } from '../components/ui';
import PlotlyChart, { PALETTE } from '../components/PlotlyChart';

const COLORS = ['#1f6fd1', '#2a2f36', '#1b7f3a', '#b26a00'];

function ParetoPanel() {
  const { scenarioId, seed, hasAmbulances, notify } = useTraffic();
  const [cross, setCross] = useState(0.5);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [lamIdx, setLamIdx] = useState(5);
  const [xmode, setXmode] = useState('cross');

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const d = await getPareto({ scenario: scenarioId, seed, cross });
      setData(d);
      setLamIdx(d.points.length - 1);
    } catch (e) {
      setErr(e.message);
      notify('ERROR', 'Pareto sweep failed', e.message);
    } finally {
      setBusy(false);
    }
  };

  const pts = (data?.points || []).filter((p) => p.mean_emergency_response_time !== null);
  const xkey = xmode === 'cross' ? 'cross_street_person_delay' : 'person_delay';
  const sel = pts[Math.min(lamIdx, pts.length - 1)];
  const base = pts[0];

  return (
    <Panel title="PARETO: AMBULANCE SPEED vs CIVILIAN DELAY" icon={<Scale size={18} color="#2a2f36" />}>
      {!hasAmbulances ? (
        <Note tone="warn">Pick a scenario with an ambulance (D, E, F or Belagavi-inspired two-ambulance) to sweep emergency priority.</Note>
      ) : (
        <>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text)' }}>
            <label>
              Cross-street demand: <strong>{cross.toFixed(2)}</strong> veh/s per junction{' '}
              <input type="range" min="0" max="0.8" step="0.05" value={cross} onChange={(e) => setCross(parseFloat(e.target.value))} />
            </label>
            <Btn onClick={run} disabled={busy}>{busy ? 'Sweeping (≈10 s)…' : 'Run sweep'}</Btn>
          </div>
          {err && <Note tone="error">{err}</Note>}
          {sel && (
            <>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text)' }}>
                <label>
                  Emergency priority λ: <strong>{sel.lambda_param}</strong>{' '}
                  <input type="range" min="0" max={pts.length - 1} step="1" value={Math.min(lamIdx, pts.length - 1)} onChange={(e) => setLamIdx(parseInt(e.target.value, 10))} />
                </label>
                <label>
                  Cost axis:{' '}
                  <select value={xmode} onChange={(e) => setXmode(e.target.value)} style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border-strong)', borderRadius: '6px' }}>
                    <option value="cross">Cross-street delay (who pays)</option>
                    <option value="total">Total civilian delay</option>
                  </select>
                </label>
              </div>
              <PlotlyChart
                height={320}
                data={[
                  {
                    type: 'scatter',
                    mode: 'lines+markers+text',
                    name: 'λ sweep (0 → 1)',
                    x: pts.map((p) => p[xkey]),
                    y: pts.map((p) => p.mean_emergency_response_time),
                    text: pts.map((p) => `λ=${p.lambda_param}`),
                    textposition: 'top center',
                    line: { color: PALETTE.purple, width: 2 },
                    marker: { size: 9, color: PALETTE.purple },
                    hovertemplate: 'λ=%{text}<br>response %{y:.0f} s<br>delay %{x:,.0f} person-s<extra></extra>',
                  },
                  {
                    type: 'scatter',
                    mode: 'markers',
                    name: 'selected λ',
                    x: [sel[xkey]],
                    y: [sel.mean_emergency_response_time],
                    marker: { size: 18, color: 'rgba(0,0,0,0)', line: { color: '#ffffff', width: 2 } },
                    hoverinfo: 'skip',
                  },
                ]}
                layout={{
                  xaxis: { title: { text: xmode === 'cross' ? 'Cross-street person-delay (person-s)' : 'Total civilian person-delay (person-s)' } },
                  yaxis: { title: { text: 'Mean ambulance response (s)' } },
                }}
              />
              <StatGrid>
                <Stat label="Ambulance response" value={`${fmt.n(sel.mean_emergency_response_time, 0)} s`} sub={`${fmt.n(sel.mean_emergency_response_time - base.mean_emergency_response_time, 0)} s vs λ=0`} color="#1b7f3a" />
                <Stat label="Cross-street delay" value={fmt.int(sel.cross_street_person_delay)} sub={`${fmt.int(sel.cross_street_person_delay - base.cross_street_person_delay)} vs λ=0`} color="#b26a00" />
                <Stat label="Arterial delay" value={fmt.int(sel.arterial_person_delay)} sub={`${fmt.int(sel.arterial_person_delay - base.arterial_person_delay)} vs λ=0`} />
                <Stat label="Total civilian delay" value={fmt.int(sel.person_delay)} sub={`${fmt.int(sel.person_delay - base.person_delay)} vs λ=0`} />
                <Stat label="Jain fairness" value={fmt.n(sel.jain_fairness_index, 3)} />
              </StatGrid>
              <Note>
                λ scales both the QUBO's emergency weight (so the chosen signal plan can change with λ) and the preemption duty cycle (share of time a preempted junction is forced green).
                What happens to arterial, cross-street and total delay depends on the scenario and on the cross-street demand set above; read the numbers, not a rule of thumb.
                This is a model result on a toy network with assumed traffic, not advice for a real junction.
              </Note>
            </>
          )}
        </>
      )}
    </Panel>
  );
}

function AdaptivePanel() {
  const { scenarioId, seed, notify } = useTraffic();
  const [interval, setInterval_] = useState(60);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      setData(await runAdaptive({ scenario: scenarioId, seed, interval }));
    } catch (e) {
      setErr(e.message);
      notify('ERROR', 'Adaptive run failed', e.message);
    } finally {
      setBusy(false);
    }
  };

  const junctions = data ? Object.keys(data.events[0].signal_plan) : [];
  const rows = data
    ? [
        ['Average wait (s / vehicle)', 'average_waiting_time', 1],
        ['Max approach wait (s)', 'max_approach_wait', 0],
        ['Jain fairness (1.0 = equal)', 'jain_fairness_index', 3],
        ['Person-delay (person-s)', 'total_person_delay', 0],
        ['Throughput (vehicles)', 'throughput', 0],
        ['Starvation violations (>120 s)', 'starvation_violations', 0],
        ['Idling CO₂ (kg, model)', 'estimated_co2_kg', 2],
      ].map(([label, key, d]) => ({ id: key, label, s: fmt.n(data.static[key], d), a: fmt.n(data.adaptive[key], d) }))
    : [];

  return (
    <Panel title="ADAPTIVE ROLLING-HORIZON vs SINGLE-SHOT PLAN" icon={<Timer size={18} color="#1f6fd1" />}>
      <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text)' }}>
        <label>
          Re-optimise every{' '}
          <select value={interval} onChange={(e) => setInterval_(parseInt(e.target.value, 10))} style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border-strong)', borderRadius: '6px' }}>
            {[30, 60, 90, 120].map((v) => <option key={v} value={v}>{v} s</option>)}
          </select>
        </label>
        <Btn onClick={run} disabled={busy}>{busy ? 'Solving each window…' : 'Run static vs adaptive'}</Btn>
      </div>
      {err && <Note tone="error">{err}</Note>}
      {data && (
        <>
          <Note>
            {data.replan_count} scheduled re-plans · QAOA solves {data.qaoa_executions} · SA fallbacks {data.sa_fallbacks}. The same seed and traffic feed both controllers.
          </Note>
          <PlotlyChart
            height={280}
            data={junctions.map((j, i) => ({
              type: 'scatter',
              mode: 'lines+markers',
              name: j,
              x: data.events.map((e) => e.simulation_time),
              y: data.events.map((e) => e.signal_plan[j]),
              line: { color: COLORS[i % COLORS.length], width: 2, shape: 'hv' },
              marker: { size: 7 },
            }))}
            layout={{ xaxis: { title: { text: 'Simulation time (s)' } }, yaxis: { title: { text: 'Green duration (s)' }, range: [10, 50] } }}
          />
          <DataTable
            columns={[
              { key: 'label', label: 'Metric' },
              { key: 's', label: 'Static plan' },
              { key: 'a', label: 'Adaptive' },
            ]}
            rows={rows}
          />
          <Note tone="warn">One seed, one scenario: indicative only. Adaptive is not guaranteed to beat the static plan, and the table shows whichever way it came out.</Note>
        </>
      )}
    </Panel>
  );
}

export default function AnalyticsPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<BarChart3 size={24} color="#1f6fd1" />}
        title="ANALYTICS & TRADE-OFFS"
        subtitle="Emergency-priority Pareto sweep and adaptive re-optimisation, both computed by the backend on the selected scenario."
      />
      <ParetoPanel />
      <AdaptivePanel />
    </div>
  );
}
