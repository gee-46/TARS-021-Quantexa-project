# QuantumFlow — Jury Demo Cheat Sheet (≈8 min)

**One-line pitch:** an adaptive, people-aware, fairness-aware traffic controller that formulates signal timing and ambulance conflicts as QUBOs, compares QAOA / SA / Greedy honestly, and shows the trade-offs. Everything is simulated.

## Before you go on
1. `.venv313\Scripts\python.exe -m uvicorn api_server:app --port 8000` → open http://127.0.0.1:8000
2. Click every step below once so results are cached (first run of each takes ~5–20 s; repeats are instant).
3. Optional backup tab: `.venv313\Scripts\python.exe -m streamlit run streamlit_app.py` (has the loader).
4. Header dropdown = scenario. Start on **E – Two conflicting ambulances**. Seed is fixed at 42, so numbers repeat.

## Run of show (numbers verified on this build, seed 42)

| # | Where / click | Say | On screen |
|---|---|---|---|
| 1 | Landing page → scroll to control center | "Hybrid quantum-classical traffic simulator." | Loader / landing visuals |
| 2 | **Overview** | "KPIs are person-based, not just vehicle counts; every card is compared with a fixed 30 s baseline." | Avg wait 86.1 s, person-delay 55,278, Jain fairness 0.76 (scenario E) |
| 3 | **Run quantum optimization → Apply** | "12 binary variables (4 junctions × 3 green times) solved by QAOA, SA and Greedy on the same QUBO." | Verdict: *"Greedy and SA won (−36.31). QAOA lost this instance (0.64 above)."* Wait 86 → 52 s, person-delay 55k → 33k, throughput 151 → 226 |
| 4 | **Emergency Corridor → Simulate green corridor** | "Two ambulances need junction I2. A 4-qubit conflict QUBO sequences them." | With solver plan: AMB_EAST 47 → 32 s, AMB_WEST 43 → 28 s. Conflict table: QAOA, SA, Greedy all 0.50 = exact optimum ("does not separate them") |
| 5 | **Analytics → Run sweep** (scenario **D**, cross-street 0.50) | "λ = how much we prioritise the ambulance; we show what it costs others." | λ 0 → 1: ambulance 60 → 44 s; cross-street delay 96.6k → 104.0k (+7.7%); arterial 23.7k → 16.8k; total ≈ flat (120.3k → 120.8k) |
| 6 | **Analytics → Run static vs adaptive** (scenario **B**, congested) | "The plan is re-solved every 60 s from live queues." | Avg wait 135.3 → 126.0 s, person-delay 200.7k → 187.0k (≈ −7%) |
| 7 | **Quantum Optimizer → Compare ideal vs noisy** (scenario E) | "Same circuit and angles; noise degrades it." | Valid orderings 28.1% → 21.8%, optimum hit 15.2% → 12.1% |
| 8 | Header → **Belagavi-inspired: peak + two ambulances** | "An illustrative topology, not a digital twin." | Amber disclaimer banner; junctions Central Bus Stand, Chennamma Circle, RPD Cross, Tilakwadi |

## Say these on purpose (they build trust)
- "QAOA lost on the optimizer instance, and tied on the ambulance conflict. We report whichever way it comes out."
- "At 12 variables exhaustive search is instant; we do **not** claim quantum advantage."
- "The solver plan cuts waiting a lot **but lowers fairness (0.76 → 0.59)**. That is why fairness is a tracked metric."
- "Ambulance priority costs cross-street users; the slider makes the cost visible."

## Likely questions
| Question | Honest answer |
|---|---|
| Real traffic data? | No. Volumes are assumed; the simulator is tested, not validated against a city. |
| Run on IBM hardware? | No. Aer simulator only. The IBM path is implemented but unverified; ideal-vs-noisy *simulation* is what we show. |
| Is Belagavi real? | Illustrative labels and assumed demand. Not a digital twin. |
| Why does a lower QUBO energy sometimes give a worse metric? | The QUBO objective is a model of traffic, not the simulator outcome; both are shown. |
| Does adaptive always help? | No. On our runs it helps under heavy congestion (B) and is neutral on A, C, D, G and Belagavi peak. |
| Turn phases? | Not modelled; preemption forces the whole junction green. |

## Don't
- Don't say "quantum advantage", "digital twin", "real-time" or "live sensors".
- Don't quote numbers from memory; if a number differs, read the screen (values change with scenario, seed, or code).
- Don't demo adaptive on scenario G or A expecting a gain.

## If something breaks
- UI shows "API unreachable" → the API terminal died; restart the uvicorn command above.
- `numpy … longdouble infinity` error → you used Python 3.14; use `.venv313\Scripts\python.exe`.
- Slow step → results are cached after the first run; pre-click each step.

## Optional slide outline (5 slides)
1. Problem: signals + emergency conflicts, people not vehicles.
2. Formulation: 12-variable QUBO; conflict QUBO (K²); fairness & person-delay metrics.
3. Honest solver comparison (QAOA vs SA vs Greedy; ties and losses shown).
4. Trade-offs: Pareto, fairness cost, adaptive only under congestion.
5. Scope & next steps: simulator-only, real IBM hardware validation, real traffic data.
