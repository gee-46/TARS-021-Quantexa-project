# QuantumFlow Upgrade Status

From: *"a QAOA traffic-light optimiser with an emergency corridor"*
To: *"an adaptive, people-aware, fairness-constrained traffic-control system that resolves emergency conflicts with QUBO/QAOA, compares solvers honestly and exposes the trade-offs."*

Everything below is reproducible with `python -m pytest tests -q` and `streamlit run streamlit_app.py`.

| # | Upgrade | Status | Where |
|---|---|---|---|
| 1 | Adaptive rolling-horizon optimisation (re-solve every 60 s) | Done | `simulation/adaptive_controller.py` |
| 2 | People instead of vehicles (occupancy, buses, person-delay) | Done | `simulation/models.py`, `optimization/traffic_objectives.py` |
| 3 | Fairness / no starvation (max wait, starvation penalty, Jain index) | Done | `optimization/traffic_objectives.py`, `simulation/engine.py` |
| 4 | Multiple ambulances resolved by a conflict QUBO | Done, **defects fixed** (see below) | `optimization/emergency_conflict.py`, `simulation/emergency_controller.py` |
| 5 | Solver arbiter: QAOA vs SA vs Greedy | Done; also for the conflict QUBO | `optimization/solver_arbiter.py`, `arbitrate_conflict` |
| 6 | Pareto slider (ambulance vs civilians) | Done, **redesigned to be a real trade-off** | `optimization/pareto.py`, dashboard tab |
| 7 | IBM hardware | Ideal-vs-noisy **simulation** verified; real-hardware path implemented but **unverified** (never run on a device) | `optimization/ibm_hardware.py` |
| 8 | Belagavi-inspired corridor | Real OpenStreetMap locations + road geometry, assumed traffic; **not** a digital twin | `simulation/belagavi.py`, `simulation/data/belagavi_geo.json` |
| - | Dashboard for all of the above | Done | `dashboard.py`, `streamlit_app.py` |

## Defects found and fixed while auditing the upgrade branch

1. **The conflict QUBO had no objective.** `build_conflict_qubo` computed each vehicle/slot delay cost but never added it to `Q`, so only the one-hot penalties existed: energy was 0 and the ambulance order was arbitrary (a priority-2 ambulance could be sequenced ahead of priority-1). The cost is now a priority-weighted packed-slot waiting time, and the one-hot penalty scales automatically so no invalid assignment can be cheaper than a valid one.
2. **Opposing ambulances crashed the simulator.** Scenario E/F (`I4 -> I3 -> I2`) raised `Non-forward corridor route transition`. Routes may now run in either direction along the arterial (direction reversals and repeated junctions are still rejected).
3. **The conflict schedule was computed but never enforced,** and every ambulance was treated as priority 1. Vehicles now carry `priority_level`, and the controller withholds preemption from an ambulance while an earlier-sequenced one is queued at, or in transit into, the contested junction (only imminent predecessors hold, so a far-away ambulance can never idle a junction).
4. **The Pareto sweep was flat.** With no cross traffic, preemption could only help civilians, so lambda > 0 gave identical points. The simulator now has optional cross-street queues (served only while the arterial is red), and lambda sets the corridor's preemption duty cycle. Per-component delay is reported so the result stays interpretable.
5. **The run-result contract omitted the new metrics.** `QuantumFlowRunResult` now carries person-delay, Jain fairness, max wait, starvation, fuel/CO2, cross-street delay and per-ambulance results, and `emergency_present` respects multi-ambulance scenarios.

## What the results honestly show

* **Solver comparison.** On the instance checked by hand (3 ambulances, 9 qubits) QAOA (Aer, p=2) found the exact optimum, but only ~0.4% of shots landed on it, and SA and Greedy found it too; the arbiter prints a tie when that is what happened. Instances where the highest-priority ambulance arrives late are ones where Greedy (priority-first) loses to SA/exact - `tests/test_upgrade_features.py::test_arbiter_reports_a_loser_honestly`. Nothing here demonstrates a quantum advantage; at these sizes exact enumeration is instant.
* **Pareto (scenario D, seed 42, QUBO plan 45 s green everywhere).** Ambulance response falls as lambda rises (46 -> 31 s at 0.1 veh/s cross demand, 60 -> 44 s at 0.5). What it costs is *cross-street* delay, which rises (e.g. 96.6k -> 104.0k person-s at 0.5, +7.7%) while arterial delay falls (23.7k -> 16.8k). **Total** civilian delay is roughly flat at heavy cross demand (+0.4%) and falls at light demand, because forced green also drains the arterial queue. So in this model emergency priority is not free for cross-street users, but it does not clearly raise total civilian delay; the dashboard plots either axis and exposes cross-street demand as a slider.
* **Hardware.** On the noisy-Aer model, sampling the tuned 4-qubit circuit gives fewer valid orderings and a lower optimum-hit rate than the ideal simulator. The noise model is generic, not a calibrated device.

## IBM hardware (opt-in)

```bash
pip install -r requirements-ibm.txt
export IBM_QUANTUM_TOKEN=...            # or QiskitRuntimeService.save_account(...)
python - <<'PY'
from optimization.emergency_conflict import requests_from_configs
from optimization.ibm_hardware import compare_simulator_vs_hardware
from simulation.scenario import create_canonical_scenarios
sc = create_canonical_scenarios()["scenario_e_two_emergency_conflict"]
reqs = requests_from_configs(sc.get_all_emergency_configs(), "I3")
print(compare_simulator_vs_hardware(reqs, shots=1024, use_hardware=True).to_dict())
PY
```

Status: **implemented, documented, unverified.** Nothing contacts IBM unless `use_hardware=True` (the dashboard requires an explicit checkbox). The hardware branch follows the documented `qiskit-ibm-runtime` `SamplerV2` API but **has not been executed against a real backend in this repository** - treat the first run as a check of the integration.

## Known limitations

* Preemption forces an *entire junction* green for the arterial; there are no per-phase turn movements.
* The conflict sequencing uses a packed-slot wait model (slots are contiguous from the earliest arrival); it is a sequencing heuristic, not a full signal-timing optimiser.
* The Belagavi content is a Belagavi-inspired corridor, not a digital twin: junction locations and road geometry are real OpenStreetMap data, but the corridor choice, signal timings and all traffic volumes are assumed, and no calibration or validation against real traffic has been done.
* Traffic volumes everywhere are simulated/assumed; none are backed by measured data.
* Turn phases are not modelled.
* Pareto results depend on the configured cross-street traffic assumption.
* QAOA is executed through classical simulation (Qiskit Aer); no real-hardware run has been performed.
* No quantum advantage is claimed.
* Single-seed simulation comparisons are indicative; use `optimization/benchmark.py` for multi-seed statistics.
