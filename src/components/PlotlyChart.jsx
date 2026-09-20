import React, { useEffect, useRef } from 'react';

// Real Plotly.js charts (bar / scatter) in the control center's dark theme.
// Plotly is loaded on demand (separate chunk) so pages without charts stay light.
// All data is passed in from API results; this component never fabricates values.

const BASE_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Segoe UI, system-ui, sans-serif', color: '#4a5560', size: 11 },
  margin: { l: 56, r: 16, t: 28, b: 46 },
  hoverlabel: { bgcolor: '#ffffff', font: { color: '#1c2229' }, bordercolor: '#aeb5bd' },
  legend: { orientation: 'h', y: 1.15, x: 1, xanchor: 'right', font: { size: 10 } },
  xaxis: { gridcolor: 'rgba(0,0,0,0.08)', zerolinecolor: 'rgba(0,0,0,0.3)' },
  yaxis: { gridcolor: 'rgba(0,0,0,0.08)', zerolinecolor: 'rgba(0,0,0,0.3)' },
};

export const PALETTE = { cyan: '#1f6fd1', green: '#1b7f3a', red: '#c62828', amber: '#e0a100', purple: '#2a2f36', indigo: '#8b949e' };

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
