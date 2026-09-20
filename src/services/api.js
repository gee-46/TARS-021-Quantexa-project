// Real backend client for the QuantumFlow Python API (api_server.py).
//
// Every function returns data computed by the Python simulation / QUBO / solver modules.
// There are NO hard-coded metrics in this file: if the API is unreachable the calls throw and the UI shows
// the error instead of falling back to invented numbers.

const BASE = import.meta.env.VITE_API_BASE || '';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError(
      'Cannot reach the QuantumFlow API. Start it with: python -m uvicorn api_server:app --port 8000',
      0,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });
const qs = (params) => new URLSearchParams(params).toString();

export const getHealth = () => request('/api/health');
export const getScenarios = () => request('/api/scenarios');
export const getNetwork = (scenario) => request(`/api/network?${qs({ scenario })}`);

/** NetworkX graph analytics (degree, centrality, cut junctions, ambulance shortest paths). */
export const getGraph = (scenario) => request(`/api/graph?${qs({ scenario })}`);

/** Run the microscopic simulator. plan omitted = fixed-time 30 s baseline. */
export const simulate = ({ scenario, seed = 42, plan = null, corridor = false, duty = 1 }) =>
  post('/api/simulate', { scenario, seed, plan, corridor, duty });

/** Build the QUBO, solve it with QAOA (Aer) + SA + Greedy, and simulate baseline vs chosen plan. */
export const optimize = ({ scenario, seed = 42, qaoaMaxiter = 30 }) =>
  post('/api/optimize', { scenario, seed, qaoa_maxiter: qaoaMaxiter });

export const runAdaptive = ({ scenario, seed = 42, interval = 60, qaoaMaxiter = 15 }) =>
  post('/api/adaptive', { scenario, seed, interval, qaoa_maxiter: qaoaMaxiter });

/** Ambulances with/without the corridor + conflict-QUBO arbiter (scenarios with emergency vehicles). */
export const runEmergency = ({ scenario, seed = 42, plan = null }) =>
  post('/api/emergency', { scenario, seed, plan });

export const getPareto = ({ scenario, seed = 42, cross = 0.5 }) =>
  request(`/api/pareto?${qs({ scenario, seed, cross })}`);

/** Ideal vs noisy SIMULATION of the conflict circuit. Real hardware is not reachable through the API. */
export const runNoise = ({ scenario, seed = 42, shots = 2048 }) =>
  post('/api/noise', { scenario, seed, shots });
