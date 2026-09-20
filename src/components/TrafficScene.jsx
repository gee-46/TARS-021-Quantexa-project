import React from 'react';
import { SCENE, laneY } from '../services/storyModel';

// Pure renderer for the road network. It draws exactly what it is given (positions, signal states, vehicles,
// ambulances, corridor) and holds no data of its own.

const CAR_COLORS = ['#8d99a6', '#c7ccd2', '#5d6875', '#aab2bb', '#d9dde2', '#7a8794', '#98a4b0'];
const { W, H, roadY, half, carLen } = SCENE;

function Housing({ x, y, on, forced }) {
  // vertical signal head: red over green
  return (
    <g>
      {forced && <rect x={x - 3} y={y - 3} width={18} height={32} rx={4} fill="none" stroke="var(--green)" strokeWidth={2} style={{ animation: 'blink 1s infinite' }} />}
      <rect x={x} y={y} width={12} height={26} rx={3} fill="#1b1e23" />
      <circle cx={x + 6} cy={y + 7} r={4} fill={on ? '#4a2a2a' : '#e5484d'} />
      <circle cx={x + 6} cy={y + 19} r={4} fill={on ? '#3ddc84' : '#24422f'} />
    </g>
  );
}

function Junction({ id, name, x, sig, label, labelTone }) {
  const main = sig?.main;
  return (
    <g>
      {/* cross street */}
      <rect x={x - half} y={26} width={half * 2} height={H - 46} fill="var(--road)" />
      <line x1={x} x2={x} y1={26} y2={roadY - half} stroke="#e8c547" strokeWidth={2} strokeDasharray="12 10" />
      <line x1={x} x2={x} y1={roadY + half} y2={H - 20} stroke="#e8c547" strokeWidth={2} strokeDasharray="12 10" />
      <line x1={x - half} x2={x - half} y1={26} y2={H - 20} stroke="var(--road-edge)" strokeWidth={2} />
      <line x1={x + half} x2={x + half} y1={26} y2={H - 20} stroke="var(--road-edge)" strokeWidth={2} />
      {/* junction box */}
      <rect x={x - half} y={roadY - half} width={half * 2} height={half * 2} fill="var(--road)" />
      {/* crosswalks */}
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <g key={i} fill="var(--lane)" opacity={0.9}>
          <rect x={x - half - 9} y={roadY - half + 3 + i * 8} width={6} height={5} />
          <rect x={x + half + 3} y={roadY - half + 3 + i * 8} width={6} height={5} />
          <rect x={x - half + 3 + i * 8} y={roadY - half - 9} width={5} height={6} />
          <rect x={x - half + 3 + i * 8} y={roadY + half + 3} width={5} height={6} />
        </g>
      ))}
      {/* signal heads: main road (EB, WB) and cross street (S, N) */}
      <Housing x={x - half - 22} y={roadY + half + 8} on={main} forced={sig?.forced} />
      <Housing x={x + half + 10} y={roadY - half - 34} on={main} forced={sig?.forced} />
      <Housing x={x + half + 10} y={roadY - half - 84} on={!main} />
      <Housing x={x - half - 22} y={roadY + half + 66} on={!main} />
      {/* junction tag */}
      <g transform={`translate(${x}, 4)`}>
        <rect x={-30} y={0} width={60} height={20} rx={3} fill="var(--charcoal)" />
        <text x={0} y={14} textAnchor="middle" fontSize={12} fontWeight={700} fill="#fff">{id}</text>
      </g>
      <text x={x} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--text-2)" fontWeight={600}>{name}</text>
      {/* queue readout */}
      {label && (
        <g transform={`translate(${x}, ${roadY + half + 112})`}>
          <rect x={-46} y={-14} width={92} height={22} rx={3} fill="var(--surface)" stroke={labelTone === 'red' ? 'var(--red)' : labelTone === 'green' ? 'var(--green)' : 'var(--border-strong)'} />
          <text x={0} y={1} textAnchor="middle" fontSize={11.5} fontWeight={700} fill="var(--text)">{label}</text>
        </g>
      )}
    </g>
  );
}

function Car({ c }) {
  const rearX = c.d > 0 ? -carLen / 2 : carLen / 2 - 3;
  const frontX = c.d > 0 ? carLen / 2 - 6 : -carLen / 2 + 2;
  return (
    <g transform={`translate(${c.x}, ${c.y})`}>
      <rect x={-carLen / 2} y={-5.5} width={carLen} height={11} rx={2.5} fill={CAR_COLORS[(c.i * 3 + Math.round(c.x)) % CAR_COLORS.length] || CAR_COLORS[0]} stroke="#4a525c" strokeWidth={0.6} />
      <rect x={frontX} y={-4} width={4} height={8} rx={1} fill="#e8eef4" opacity={0.85} />
      <rect x={rearX} y={-4.5} width={3} height={9} rx={1} fill="#d64545" />
    </g>
  );
}

function Ambulance({ a, showHalo }) {
  return (
    <g transform={`translate(${a.x}, ${a.y})`}>
      {showHalo && <circle r={26} fill="none" stroke="var(--red)" strokeWidth={2} style={{ animation: 'blink 0.9s infinite' }} />}
      <g transform={`scale(${a.dir}, 1)`}>
        <rect x={-19} y={-8.5} width={38} height={17} rx={3.5} fill="#ffffff" stroke="#2a2f36" strokeWidth={1} />
        <rect x={-19} y={-1.5} width={38} height={4} fill="#d93025" />
        <rect x={9} y={-6.5} width={8} height={7} rx={1.5} fill="#9fc4e8" />
        <g transform="translate(-6, -3)">
          <rect x={-1.6} y={-5} width={3.2} height={10} fill="#d93025" />
          <rect x={-5} y={-1.6} width={10} height={3.2} fill="#d93025" />
        </g>
        <rect x={-2} y={-11.5} width={5} height={3} fill="#d93025" style={{ animation: 'strobe 0.5s infinite' }} />
        <rect x={4} y={-11.5} width={5} height={3} fill="#1f6fd1" style={{ animation: 'strobe 0.5s infinite reverse' }} />
      </g>
      <text x={0} y={-16} textAnchor="middle" fontSize={10.5} fontWeight={700} fill="var(--red)" paintOrder="stroke" stroke="#fff" strokeWidth={3}>{a.label}</text>
    </g>
  );
}

export default function TrafficScene({ ids, xs, names = {}, signals = {}, cars = [], ambulances = [], routes = [], corridor = false, queueLabels = {}, queueTones = {}, ariaLabel = 'Traffic network' }) {
  const first = xs[ids[0]];
  const last = xs[ids[ids.length - 1]];
  const gaps = [];
  gaps.push([12, first - half - 22]);
  for (let i = 0; i < ids.length - 1; i++) gaps.push([xs[ids[i]] + half + 22, xs[ids[i + 1]] - half - 22]);
  gaps.push([last + half + 22, W - 12]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block', background: '#e6e9e4' }} role="img" aria-label={ariaLabel}>
      {/* city blocks */}
      {gaps.map(([a, b], gi) => (
        <g key={gi}>
          {[[34, 128], [roadY + half + 30, 108]].map(([y, h], bi) => (
            <g key={bi}>
              <rect x={a} y={y} width={Math.max(0, b - a)} height={h} rx={3} fill={(gi + bi) % 4 === 0 ? '#cfdcc9' : '#d6dad3'} />
              {(gi + bi) % 4 !== 0 && b - a > 60 && [0, 1, 2].map((k) => (
                <rect key={k} x={a + 8 + k * ((b - a - 16) / 3)} y={y + 8 + ((k + gi) % 2) * 10} width={(b - a - 16) / 3 - 8} height={h - 26 - ((k + gi) % 2) * 10} rx={2} fill={['#c5cad2', '#cdd1d7', '#bfc5cc'][(k + bi + gi) % 3]} />
              ))}
            </g>
          ))}
        </g>
      ))}

      {/* main road */}
      <rect x={0} y={roadY - half} width={W} height={half * 2} fill="var(--road)" />
      <line x1={0} x2={W} y1={roadY - half} y2={roadY - half} stroke="var(--road-edge)" strokeWidth={2} />
      <line x1={0} x2={W} y1={roadY + half} y2={roadY + half} stroke="var(--road-edge)" strokeWidth={2} />
      <line x1={0} x2={W} y1={roadY} y2={roadY} stroke="#e8c547" strokeWidth={2} strokeDasharray="14 12" />

      {/* junctions + cross streets */}
      {ids.map((id) => (
        <Junction key={id} id={id} name={names[id] || ''} x={xs[id]} sig={signals[id]} label={queueLabels[id]} labelTone={queueTones[id]} />
      ))}

      {/* emergency corridor overlay */}
      {corridor && routes.map((r) => {
        const x0 = xs[r.route[0]] - r.dir * (half + 4 + 118);
        const x1 = xs[r.route[r.route.length - 1]] + r.dir * (half + 40);
        const y = laneY(r.dir);
        return (
          <g key={r.id}>
            <line x1={x0} x2={x1} y1={y} y2={y} stroke="var(--green)" strokeWidth={22} opacity={0.28} strokeLinecap="round" />
            <line x1={x0} x2={x1} y1={y} y2={y} stroke="#8be0a4" strokeWidth={3} strokeDasharray="10 8" style={{ animation: `routeFlow ${r.dir > 0 ? '' : 'reverse '}0.9s linear infinite` }} />
            {r.route.map((id) => (
              <rect key={id} x={xs[id] - half - 2} y={roadY - half - 2} width={half * 2 + 4} height={half * 2 + 4} fill="none" stroke="var(--green)" strokeWidth={3} rx={3} />
            ))}
          </g>
        );
      })}

      {/* queued vehicles */}
      {cars.map((c) => <Car key={c.key} c={c} />)}

      {/* ambulances (drawn last, on top) */}
      {ambulances.map((a) => <Ambulance key={a.id} a={a} showHalo={a.stuck} />)}

    </svg>
  );
}
