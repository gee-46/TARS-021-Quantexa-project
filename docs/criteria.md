# Evaluation criteria: what is implemented, how to see it, and its limits

Everything here is simulated on assumed traffic (no measured data, no real-world validation). QAOA runs on the Qiskit Aer
simulator; no quantum advantage is claimed. Numbers below are from seed 42 and can be reproduced with the commands shown.

## 1. Hybrid quantum-classical optimisation
* **What:** signal timing is a 12-variable QUBO (4 junctions x {15, 30, 45} s) -> Ising Hamiltonian -> QAOA circuit on Aer with a
  classical COBYLA outer loop, with automatic simulated-annealing fallback (`optimization/hybrid_solver.py`). A solver arbiter runs
  QAOA, SA and Greedy on the same QUBO and reports the winner, including losses and ties. Ambulance conflicts use a second small QUBO.
* **See it:** Live Traffic > Optimisation panel; Optimisation > Signal optimisation; Solver comparison.
* **Limits:** simulator only; real IBM hardware path is implemented but unverified. QAOA often ties or loses to SA/Greedy at this size.

## 2. Multi-intersection traffic signal management
* **What:** four junctions optimised jointly (upstream/downstream coupling terms in one QUBO), re-planned every 60 s from live queues
  (adaptive rolling horizon), person-weighted, with fairness (Jain index) and starvation tracking. New: a **cross-street delay term**
  (`optimization/traffic_objectives.py::add_cross_street_term`, weight `CROSS_STREET_WEIGHT = 0.5`), on only when a scenario models cross
  traffic. Without it the objective ignored cross streets and chose "45 s everywhere", which under heavy cross traffic nearly doubled total
  civilian delay (scenario D, 0.5 veh/s: 120k vs 68k person-seconds for the fixed plan). The weight was calibrated by simulation sweep over
  five cross-traffic cases (worst-case regret 4.2% at 0.5 vs 85% at 0); this is an in-sample calibration.
* **Limits:** one straight arterial (no grid), fixed 60 s cycle, three green durations, no turn phases.

## 3. Emergency-vehicle green corridor routing
* **What:** corridor preemption along the ambulance route with lookahead; multiple ambulances sequenced by a conflict QUBO. New: a
  **queue-aware route planner** (`simulation/route_planner.py`, NetworkX) that ranks paths by hop time plus expected queue delay
  (`queue x cycle / (service x green)`) from the simulated queues, plus a **Dispatch** panel (Emergency page, `POST /api/route-plan`):
  choose origin and destination, the route is planned, and the same simulator runs it with and without the corridor.
* **Limits:** this arterial is a path graph, so each origin/destination has exactly one route; the planner is tested on a graph with a
  bypass (`tests/test_criteria_upgrades.py`) but the simulator only drives monotone arterial routes, so alternatives cannot be simulated
  end to end. Preemption forces the whole junction green; the expected delay is an estimate, response times are simulator outputs.

## 4. Emissions and fuel reduction simulation
* **What:** an idling fuel/CO2 model (0.7 L per vehicle-hour, 2.31 kg CO2 per litre; `simulation/emissions.py`) applied to **all** stationary
  civilian vehicles, now including cross-street vehicles (previously arterial only, which overstated the benefit in cross-traffic
  scenarios: Belagavi peak went from -15.5% to -6.9% after the fix). Fuel and CO2 are shown on the Live Traffic screen for the fixed 30 s
  plan, a rule-based controller and the QUBO plan, and on the comparison page and metrics tiles.
* **Result (modelled CO2 vs the fixed 30 s plan):** balanced -39%, congested -11%, bus corridor -36%, two ambulances -40%,
  high demand -18%, Belagavi-inspired peak -7%.
* **Limits:** idling-only (no speed/acceleration effects); the constants are assumed; the reference plans are simple; the emergency
  corridor itself does not change emissions (12.41 -> 12.39 kg on scenario E).
