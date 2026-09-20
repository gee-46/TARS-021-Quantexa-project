import React from 'react';
import { AlertTriangle, Play } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { PageHeader, Panel, DataTable, Note, Btn } from '../components/ui';

const sevColor = { INFO: '#38bdf8', ERROR: '#ef4444', EMERGENCY: '#f87171', WARNING: '#f59e0b' };

export default function EventsPage() {
  const { scenarios, scenarioId, selectScenario, loading, activeEvents } = useTraffic();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<AlertTriangle size={24} color="#f59e0b" />}
        title="SCENARIOS & EVENTS"
        subtitle="Each scenario is a real simulator configuration served by the backend. Loading one re-runs the fixed-time baseline."
      />

      <Panel title="SCENARIO LIBRARY">
        <DataTable
          columns={[
            { key: 'title', label: 'Scenario', render: (s) => <strong style={{ color: s.id === scenarioId ? '#6ee7b7' : '#fff' }}>{s.title}</strong> },
            { key: 'amb', label: 'Ambulances', render: (s) => s.ambulances },
            { key: 'cross', label: 'Cross-street traffic', render: (s) => (s.has_cross_street_traffic ? 'yes' : 'no') },
            { key: 'dur', label: 'Horizon', render: (s) => `${s.duration_seconds} s` },
            {
              key: 'act',
              label: '',
              render: (s) => (
                <Btn tone="ghost" disabled={loading || s.id === scenarioId} onClick={() => selectScenario(s.id)}>
                  <Play size={13} /> {s.id === scenarioId ? 'Loaded' : 'Load'}
                </Btn>
              ),
            },
          ]}
          rows={scenarios}
          emptyText="No scenarios (API offline?)."
        />
        <Note tone="warn">
          Accidents, lane closures and reroutes are not modelled by the simulator, so they are not offered here. Heavy demand is scenario B/G, ambulances are D/E/F.
          The “Belagavi-inspired” scenarios use assumed demand on real OpenStreetMap junction locations.
        </Note>
      </Panel>

      <Panel title="SESSION LOG">
        <DataTable
          columns={[
            { key: 'timestamp', label: 'Time' },
            { key: 'severity', label: 'Level', render: (e) => <span style={{ color: sevColor[e.severity] || '#c4b5fd', fontWeight: 700 }}>{e.severity}</span> },
            { key: 'title', label: 'Event', render: (e) => <strong>{e.title}</strong> },
            { key: 'location', label: 'Where' },
            { key: 'description', label: 'Detail', render: (e) => <span style={{ color: 'rgba(196,181,253,.85)' }}>{e.description}</span> },
          ]}
          rows={activeEvents}
          emptyText="No events yet."
        />
      </Panel>
    </div>
  );
}
