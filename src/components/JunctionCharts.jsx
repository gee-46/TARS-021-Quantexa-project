import React from 'react';
import { useTraffic } from '../context/TrafficContext';
import PlotlyChart, { PALETTE } from './PlotlyChart';
import { Panel, Note } from './ui';

// Per-junction Plotly charts built from the simulator run currently shown (and the fixed-time baseline run).
export default function JunctionCharts() {
  const { metrics: m, baselineMetrics: b, network, currentPlan, intersections } = useTraffic();
  if (!m || !b || !network) return null;

  const ids = network.nodes.map((n) => n.id);
  const label = (id) => `${id}`;
  const cycle = network.cycle_length;
  const green = ids.map((id) => currentPlan?.[id] ?? intersections[id]?.signalDuration ?? 0);

  return (
    <Panel title="PER-JUNCTION CHARTS (SIMULATED)">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        <PlotlyChart
          height={260}
          data={[
            { type: 'bar', name: 'Fixed 30 s baseline', x: ids.map(label), y: ids.map((i) => b.approach_mean_queue[i]), marker: { color: PALETTE.indigo } },
            { type: 'bar', name: 'Plan shown', x: ids.map(label), y: ids.map((i) => m.approach_mean_queue[i]), marker: { color: PALETTE.cyan } },
          ]}
          layout={{ title: { text: 'Mean queue (vehicles)', x: 0.02, xanchor: 'left', font: { size: 12, color: '#1c2229' } }, barmode: 'group' }}
        />
        <PlotlyChart
          height={260}
          data={[
            { type: 'bar', name: 'Mean head wait', x: ids.map(label), y: ids.map((i) => m.approach_mean_head_wait[i]), marker: { color: PALETTE.amber } },
            { type: 'bar', name: 'Max head wait', x: ids.map(label), y: ids.map((i) => m.approach_max_head_wait[i]), marker: { color: PALETTE.red } },
          ]}
          layout={{ title: { text: 'Front-of-queue wait (s)', x: 0.02, xanchor: 'left', font: { size: 12, color: '#1c2229' } }, barmode: 'group' }}
        />
        <PlotlyChart
          height={260}
          data={[
            { type: 'bar', name: 'Green', x: ids.map(label), y: green, marker: { color: PALETTE.green } },
            { type: 'bar', name: 'Red', x: ids.map(label), y: green.map((g) => cycle - g), marker: { color: PALETTE.red } },
          ]}
          layout={{ title: { text: `Signal timing in a ${cycle} s cycle (s)`, x: 0.02, xanchor: 'left', font: { size: 12, color: '#1c2229' } }, barmode: 'stack' }}
        />
      </div>
      <Note>Head wait = waiting time of the vehicle at the front of each queue, averaged (or maximised) over the run. All values come from the simulator, not sensors.</Note>
    </Panel>
  );
}
