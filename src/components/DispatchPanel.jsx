import React, { useEffect, useState } from 'react';
import { Route, ArrowRight } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { planRoute } from '../services/api';
import { Panel, DataTable, Note, Btn, StatGrid, Stat, fmt } from './ui';

// Dispatch an ambulance: the backend plans its route on the junction graph (NetworkX, queue-aware) and then the same
// simulator runs it with and without the green corridor. Response times are simulator outputs; expected delays are estimates.
export default function DispatchPanel() {
  const { network, scenarioId, seed, notify } = useTraffic();
  const ids = (network?.nodes || []).map((n) => n.id);
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ids.length) return;
    const a = network.ambulances?.[0];
    setOrigin(a ? a.route[0] : ids[0]);
    setDestination(a ? a.route[a.route.length - 1] : ids[ids.length - 1]);
    setResult(null);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, ids.length]);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await planRoute({ scenario: scenarioId, origin, destination, seed }));
    } catch (e) {
      setError(e.message);
      notify('ERROR', 'Route planning failed', e.message);
    } finally {
      setBusy(false);
    }
  };

  const sel = { fontFamily: 'inherit', fontSize: '0.82rem', padding: '5px 8px', border: '1px solid var(--border-strong)', borderRadius: 4, background: 'var(--surface)', color: 'var(--text)' };
  const r = result?.route;
  const off = result?.without_corridor;
  const on = result?.with_corridor;

  return (
    <Panel title="Dispatch an ambulance: route planning + corridor" icon={<Route size={15} />}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', fontSize: '0.82rem' }}>
        <label>Origin{' '}
          <select value={origin} onChange={(e) => setOrigin(e.target.value)} style={sel} aria-label="Origin junction">
            {ids.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </label>
        <ArrowRight size={14} color="var(--muted)" />
        <label>Destination{' '}
          <select value={destination} onChange={(e) => setDestination(e.target.value)} style={sel} aria-label="Destination junction">
            {ids.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </label>
        <Btn onClick={run} disabled={busy || !origin || origin === destination}>{busy ? 'Planning…' : 'Plan route & simulate corridor'}</Btn>
      </div>
      {origin === destination && origin && <Note tone="warn">Choose different origin and destination junctions.</Note>}
      {error && <Note tone="error">{error}</Note>}

      {r && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: '0.95rem', fontWeight: 700 }}>
            Planned route:
            {r.path.map((n, i) => (
              <React.Fragment key={n}>
                {i > 0 && <ArrowRight size={14} color="var(--muted)" />}
                <span style={{ padding: '1px 8px', borderRadius: 3, background: 'var(--green-bg)', border: '1px solid var(--green)', color: 'var(--green)' }}>{n}</span>
              </React.Fragment>
            ))}
          </div>
          <DataTable
            columns={[
              { key: 'j', label: 'Junction entered', render: (x) => <strong>{x.j}</strong> },
              { key: 'd', label: 'Expected queue delay (estimate)', render: (x) => `${fmt.n(x.d, 0)} s` },
            ]}
            rows={r.path.slice(1).map((j) => ({ id: j, j, d: r.junction_delay[j] }))}
          />
          <StatGrid min={150}>
            <Stat label="Response, no corridor (simulated)" value={off.response_time === null ? 'unfinished' : `${fmt.n(off.response_time, 0)} s`} color="var(--red)" />
            <Stat label="Response, corridor (simulated)" value={on.response_time === null ? 'unfinished' : `${fmt.n(on.response_time, 0)} s`} color="var(--green)" />
            <Stat label="Time saved" value={off.response_time !== null && on.response_time !== null ? `${fmt.n(off.response_time - on.response_time, 0)} s` : '—'} />
            <Stat label="Planning estimate (delay + travel)" value={`${fmt.n(r.expected_total_seconds, 0)} s`} sub="not a simulator output" />
          </StatGrid>
          <Note tone={r.unique_path ? 'info' : 'ok'}>
            {r.unique_path
              ? 'Only one path exists between these junctions on this arterial, so the planner returns it; on a network with alternatives it ranks them by hop time plus expected queue delay.'
              : `Cheaper than ${r.alternatives.length} alternative route(s).`}
            {' '}{result.note}
          </Note>
        </>
      )}
    </Panel>
  );
}
