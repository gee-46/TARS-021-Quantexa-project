# React Control Center: Audit and Backend Integration

Teammate commit audited and merged: `9c3a279` (`feature/dashboard`, "QuantumForce 3D launcher and interactive traffic control center").

## Audit of the merged commit

| Area | Finding |
|---|---|
| Security | No secrets, `eval`, `innerHTML` or `dangerouslySetInnerHTML`. The only external requests are two Google Fonts CSS imports. |
| Build | `npm ci && npm run build` succeeds. |
| Data layer | **Entirely mock.** `services/api.js` returned constants: "QAOA" was a `setTimeout` multiplying densities by 0.65, with a hard-coded cost `-1842.38`, "24 variables", and typed-in KPIs (-38 % wait, +36.8 % throughput, -37.6 % ambulance ETA, -25 % CO2) and "classical vs quantum" time series. |
| Model mismatch | The UI modelled a fictional 6-hub city plus a hospital. The backend is a 4-junction arterial (I1-I4). |
| Claims | Copy referred to SUMO/IoT telemetry, "IBM Quantum / Braket QPU ready", "24-qubit noiseless" simulation and outcome numbers that no code computed. These conflict with the project's honesty constraints (no fabricated results, no quantum advantage). |

## What was changed

The visual system (landing page, orb, layout, sidebar, network canvas, cards) is your teammate's and is kept. The **Streamlit loader (`frontend/webthreads`, `streamlit_app.py` loader flow) is untouched.**

* `api_server.py` (FastAPI) exposes the real modules: scenario registry, `TrafficSimulator`, QUBO builder + solver arbiter (QAOA/SA/Greedy), adaptive controller, emergency corridor + conflict-QUBO arbiter, Pareto sweep, ideal-vs-noisy simulation. It serves the built UI at `/` when `dist/` exists.
* `src/services/api.js` now performs real `fetch` calls. If the API is down the UI shows an error banner; there is no silent fallback to invented numbers.
* `src/context/TrafficContext.jsx`, `KpiCards`, `IntersectionDetailModal`, `OptimizationPipeline`, `EmergencyCorridorPanel`, `TopStatusBar` and the pages were re-based on the real 4-junction data. Events/Analytics/Comparison/Architecture pages were rewritten around backend results; the QUBO explanation modal describes the implemented 12-variable formulation.
* Removed as unsupported by the simulator: accident and road-closure "events", the hospital node, GPS/telemetry wording, SUMO/IoT/QPU-ready claims and every hard-coded KPI.
* Real-hardware IBM execution is **not reachable through the HTTP API** by design.

## Running it

```bash
pip install -r requirements.txt
npm ci && npm run build
python -m uvicorn api_server:app --port 8000     # UI + API on http://127.0.0.1:8000
# development with hot reload:  npm run dev   (proxies /api to 127.0.0.1:8000)
```

The Streamlit command center (`streamlit run streamlit_app.py`, loader first) remains available.

## Verification performed

* `tests/test_api_server.py`: 15 tests against the real modules through HTTP (schemas, determinism, 404/422 handling, strict JSON, hardware not reachable).
* Browser test in headless Edge over the DevTools protocol against the API-served build: 34 checks (dashboard, optimise + apply, emergency corridor with conflict arbiter, every page, ideal-vs-noisy noise comparison, Pareto sweep, adaptive run, Belagavi-inspired scenario + disclaimer, landing page, zero console errors). The script is environment-specific (Edge path) and is not part of the repository.

## Known limitations

* UI values are simulated with assumed traffic; the signal colour is the simulator's cyclic rule on a looping model clock.
* "Queue load %" is a display scale (mean queue / 40 vehicles), not a measured capacity.
* The topology animation (moving dots) is decorative and does not encode data.
* Preemption forces whole-junction green; turn phases are not modelled.
* Scenario results are for a fixed seed (42); differences are indicative, not statistically established.
* Two Google Fonts CSS imports remain (an external request at load time; offline the UI falls back to system fonts).
