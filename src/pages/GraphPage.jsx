import React, { useEffect, useState } from 'react';
import { Share2 } from 'lucide-react';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import PlotlyChart, { PALETTE } from '../components/PlotlyChart';
import { useTraffic } from '../context/TrafficContext';
import { getGraph } from '../services/api';
import { PageHeader, Panel, DataTable, Note, Stat, StatGrid, fmt } from '../components/ui';

// Graph analytics computed on the server with the real NetworkX library (GET /api/graph).
export default function GraphPage() {
  const { scenarioId } = useTraffic();
  const [g, setG] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setG(null);
    setErr(null);
    getGraph(scenarioId)
      .then((d) => !cancelled && setG(d))
      .catch((e) => !cancelled && setErr(e.message));
    return () => {
      cancelled = true;
    };
  }, [scenarioId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<Share2 size={24} color="#2a2f36" />}
        title="NETWORK GRAPH (NETWORKX)"
        subtitle="The junction graph is analysed with NetworkX on the backend: degree, centrality, cut junctions and ambulance shortest paths."
      />

      {err && <Note tone="error">{err}</Note>}
      {!g && !err && <Note>Computing graph analytics…</Note>}

      {g && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '20px' }}>
            <TrafficNetworkVisualizer />
            <Panel title="GRAPH SUMMARY">
              <StatGrid min={110}>
                <Stat label="Library" value={g.library} />
                <Stat label="Nodes / edges" value={`${g.graph.nodes} / ${g.graph.edges}`} />
                <Stat label="Connected" value={g.graph.connected ? 'yes' : 'no'} />
                <Stat label="Diameter" value={`${g.graph.diameter_hops} hops`} />
                <Stat label="Density" value={fmt.n(g.graph.density, 2)} />
                <Stat label="Path graph" value={g.graph.is_path_graph ? 'yes' : 'no'} />
              </StatGrid>
              <Note>{g.note}</Note>
            </Panel>
          </div>

          <Panel title="NODE METRICS">
            <PlotlyChart
              height={260}
              data={[
                { type: 'bar', name: 'Betweenness', x: g.nodes.map((n) => n.id), y: g.nodes.map((n) => n.betweenness), marker: { color: PALETTE.purple } },
                { type: 'bar', name: 'Closeness', x: g.nodes.map((n) => n.id), y: g.nodes.map((n) => n.closeness), marker: { color: PALETTE.cyan } },
              ]}
              layout={{ barmode: 'group', yaxis: { title: 'centrality' } }}
            />
            <DataTable
              columns={[
                { key: 'id', label: 'Node', render: (n) => <strong>{n.id}</strong> },
                { key: 'name', label: 'Label' },
                { key: 'degree', label: 'Degree' },
                { key: 'betweenness', label: 'Betweenness', render: (n) => fmt.n(n.betweenness, 3) },
                { key: 'closeness', label: 'Closeness', render: (n) => fmt.n(n.closeness, 3) },
                { key: 'cut', label: 'Cut junction', render: (n) => (n.is_articulation_point ? <span style={{ color: '#b26a00', fontWeight: 700 }}>yes: removing it splits the corridor</span> : 'no') },
              ]}
              rows={g.nodes}
            />
          </Panel>

          <Panel title="AMBULANCE SHORTEST PATHS (weighted by simulator hop time)">
            <DataTable
              columns={[
                { key: 'vehicle_id', label: 'Vehicle', render: (a) => <strong>{a.vehicle_id}</strong> },
                { key: 'route', label: 'Scenario route', render: (a) => a.route.join(' → ') },
                { key: 'shortest_path', label: 'NetworkX shortest path', render: (a) => a.shortest_path.join(' → ') },
                { key: 'same', label: 'Route is shortest', render: (a) => (a.route_is_shortest ? 'yes' : 'no') },
                { key: 't', label: 'Free-flow travel', render: (a) => `${a.travel_time_s} s` },
              ]}
              rows={g.ambulance_paths.map((a) => ({ id: a.vehicle_id, ...a }))}
              emptyText="This scenario has no ambulances."
            />
          </Panel>
        </>
      )}
    </div>
  );
}
