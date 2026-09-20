import React, { useEffect, useRef } from 'react';

// Real Plotly.js charts (bar / scatter) in the control center's dark theme.
// Plotly is loaded on demand (separate chunk) so pages without charts stay light.
// All data is passed in from API results; this component never fabricates values.

const BASE_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#94a3b8', size: 11 },
  margin: { l: 56, r: 16, t: 28, b: 46 },
  hoverlabel: { bgcolor: '#0f172a', font: { color: '#f8fafc' }, bordercolor: 'rgba(255,255,255,0.15)' },
  legend: { orientation: 'h', y: 1.15, x: 1, xanchor: 'right', font: { size: 10 } },
  xaxis: { gridcolor: 'rgba(255,255,255,0.07)', zerolinecolor: 'rgba(255,255,255,0.15)' },
  yaxis: { gridcolor: 'rgba(255,255,255,0.07)', zerolinecolor: 'rgba(255,255,255,0.15)' },
};

export const PALETTE = { cyan: '#38bdf8', green: '#4edea3', red: '#f87171', amber: '#fbbf24', purple: '#a78bfa', indigo: '#6366f1' };

export default function PlotlyChart({ data, layout = {}, height = 300 }) {
  const ref = useRef(null);
  const plotly = useRef(null);

  useEffect(() => {
    let cancelled = false;
    import('plotly.js-basic-dist-min').then((mod) => {
      const Plotly = mod.default;
      const el = ref.current;
      if (cancelled || !el) return;
      plotly.current = Plotly;
      const merged = {
        ...BASE_LAYOUT,
        ...layout,
        height,
        xaxis: { ...BASE_LAYOUT.xaxis, ...layout.xaxis },
        yaxis: { ...BASE_LAYOUT.yaxis, ...layout.yaxis },
      };
      Plotly.react(el, data, merged, { displayModeBar: false, responsive: true });
    });
    return () => {
      cancelled = true;
    };
  }, [data, layout, height]);

  useEffect(() => {
    const el = ref.current;
    return () => {
      if (el && plotly.current) plotly.current.purge(el);
    };
  }, []);

  return <div ref={ref} style={{ width: '100%', minHeight: height }} />;
}
