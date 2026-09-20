import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Map as MapIcon } from 'lucide-react';
import { useTraffic } from '../context/TrafficContext';
import { PageHeader, Panel, Note } from '../components/ui';

const signalColor = (s) => (s === 'GREEN' ? '#4edea3' : s === 'YELLOW' ? '#ffd700' : '#ef4444');
const loadColor = (load) => (load > 85 ? '#ef4444' : load > 55 ? '#f59e0b' : '#38bdf8');

// Leaflet map (the JS counterpart of the folium map in the legacy Streamlit app).
// Junction positions and road geometry are REAL OpenStreetMap data served by the API (fetched once, see
// examples/fetch_belagavi_geo.py). The traffic drawn on them is simulated.
export default function MapPage() {
  const { network, intersections, emergencyCorridorActive, emergencyRoutes, scenarioId } = useTraffic();
  const geo = network?.geo;

  if (!geo) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
        <PageHeader icon={<MapIcon size={24} color="#38bdf8" />} title="CORRIDOR MAP" subtitle="Waiting for the network from the API…" />
      </div>
    );
  }

  const pos = Object.fromEntries(geo.points.map((p) => [p.id, [p.lat, p.lon]]));
  const place = Object.fromEntries(geo.points.map((p) => [p.id, p]));
  const legGeometry = Object.fromEntries((geo.legs || []).map((l) => [`${l.from}-${l.to}`, l]));
  const bounds = (geo.legs || []).flatMap((l) => l.geometry).concat(geo.points.map((p) => [p.lat, p.lon]));
  const onCorridor = (a, b) =>
    emergencyCorridorActive &&
    emergencyRoutes.some(({ route }) => route.some((id, i) => i < route.length - 1 && ((id === a && route[i + 1] === b) || (id === b && route[i + 1] === a))));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', width: '100%' }}>
      <PageHeader
        icon={<MapIcon size={24} color="#38bdf8" />}
        title="CORRIDOR MAP"
        subtitle="Real Belagavi locations and roads (OpenStreetMap); junctions coloured by their simulated signal, road legs by upstream queue load."
      />
      <Note tone="warn">
        <strong>Real locations, simulated traffic.</strong> {geo.note}
      </Note>
      <Panel style={{ padding: '12px' }}>
        <div className="dark-osm" style={{ height: '520px', borderRadius: '10px', overflow: 'hidden' }}>
          <MapContainer key={scenarioId} bounds={bounds} boundsOptions={{ padding: [60, 60] }} scrollWheelZoom={false} style={{ height: '100%', width: '100%', background: '#0b1020' }}>
            <TileLayer
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              maxZoom={19}
            />
            {network.edges.map((e) => {
              const from = intersections[e.from];
              const corridor = onCorridor(e.from, e.to);
              const leg = legGeometry[`${e.from}-${e.to}`];
              return (
                <Polyline
                  key={e.id}
                  positions={leg ? leg.geometry : [pos[e.from], pos[e.to]]}
                  pathOptions={{ color: corridor ? '#4edea3' : loadColor(from?.density ?? 0), weight: corridor ? 9 : 6, opacity: 0.85 }}
                >
                  <Tooltip sticky>
                    <b>{place[e.from]?.place} → {place[e.to]?.place}</b>
                    <br />{leg ? `Road distance ${(leg.distance_m / 1000).toFixed(1)} km · ` : ''}Upstream queue load: {from?.density ?? '—'}%
                    {corridor && <><br />On an ambulance route (corridor active)</>}
                  </Tooltip>
                </Polyline>
              );
            })}
            {network.nodes.map((n) => {
              const node = intersections[n.id];
              if (!node) return null;
              return (
                <CircleMarker
                  key={n.id}
                  center={pos[n.id]}
                  radius={13}
                  pathOptions={{ color: '#ffffff', weight: 2, fillColor: signalColor(node.signal), fillOpacity: 0.95 }}
                >
                  <Tooltip direction="top" offset={[0, -10]}>
                    <b>{place[n.id]?.place ?? node.name} ({n.id})</b>
                    <br />Signal: {node.signal} · green {node.signalDuration}s of {network.cycle_length}s
                    <br />Mean queue: {node.queue} veh · load {node.density}%
                    <br />Mean head wait: {node.meanHeadWait === undefined ? '—' : `${Math.round(node.meanHeadWait)} s`}
                  </Tooltip>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        <div style={{ fontSize: '0.68rem', color: 'rgba(167, 139, 250, 0.65)', padding: '8px 4px 0' }}>
          {geo.attribution} Retrieved {geo.retrieved}. Basemap tiles come from OpenStreetMap and need an internet connection; markers and roads are drawn without it.
          Queue and signal values are simulated (the signal colour follows the simulator's cyclic rule on a looping model clock).
        </div>
      </Panel>
    </div>
  );
}
