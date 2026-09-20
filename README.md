# QuantumFlow — Hybrid Quantum-Classical Traffic Signal Optimization

QuantumFlow is a hybrid quantum-classical traffic optimization system designed for coordinated multi-intersection networks. The platform couples gate-level Quantum Approximate Optimization Algorithm (QAOA) formulation on Qiskit Aer with classical simulated annealing fallback, discrete-time microscopic traffic simulation, and a real-time dynamic emergency green corridor preemption system.

---

## 1. Project Overview

QuantumFlow addresses the combinatorial challenge of multi-intersection traffic signal timing by formulating green-duration allocation as a Quadratic Unconstrained Binary Optimization (QUBO) problem, mapping it to an Ising Hamiltonian, and solving it via a hybrid quantum-classical pipeline:

- **QUBO Formulation**: Formulates multi-intersection timing decisions into a 12-variable binary quadratic objective.
- **Ising Mapping**: Converts the upper-triangular QUBO to an Ising spin Hamiltonian ($s_i \in \{-1, +1\}$) with exact energy equivalence.
- **Gate-Level QAOA**: Executes parameterized quantum circuits on Qiskit Aer using COBYLA classical parameter optimization.
- **Classical Operational Fallback**: Utilizes classical Simulated Annealing (`dwave-neal`) on the identical QUBO model if QAOA times out, fails, or produces an operationally invalid candidate.
- **Microscopic Traffic Simulation**: Simulates second-by-second vehicle queuing, Poisson arrivals, and inter-intersection transit over a 4-intersection network.
- **Dynamic Emergency Green Corridor**: Coordinates dynamic signal preemption and downstream green wave preparation along emergency routes at runtime.
- **Comprehensive Telemetry & Contract**: Emits JSON-serializable structured metrics and objective comparative deltas.

> [!NOTE]
> **Scientific Scope & Boundary**:
> - QAOA operates as an offline combinatorial optimization solver for baseline traffic timing.
> - The real-time dynamic emergency green corridor operates as classical runtime control logic.
> - Emergency preemption does **not** alter the offline QUBO formulation or re-execute quantum circuits during live transit.
> - **No quantum speedup, quantum supremacy, or quantum advantage over classical computing is claimed.**

---

## 2. Problem Statement

The platform optimizes a 4-intersection arterial network:

$$\text{I1} \longrightarrow \text{I2} \longrightarrow \text{I3} \longrightarrow \text{I4}$$

For each intersection $i \in \{\text{I1}, \text{I2}, \text{I3}, \text{I4}\}$, the controller must select exactly one green phase duration from three discrete candidates within a fixed 60-second cycle length:

$$t_i \in \{15\text{s}, 30\text{s}, 45\text{s}\}$$

The objective balances five competing real-world traffic dynamics:
1. **Waiting Time Minimization**: Reducing queue delays across all approaches.
2. **Capacity Pressure Relief**: Allocating longer green phases to approaches nearing saturation.
3. **Throughput Maximization**: Maximizing vehicle clearance during allocated green windows.
4. **Inter-Intersection Coupling**: Synchronizing downstream green phases to prevent gridlock and queue spillback between adjacent intersections.
5. **Emergency Route Prioritization**: Prioritizing static throughput along designated emergency routes.

---

## 3. System Architecture

```
                       TRAFFIC DEMAND & QUEUE STATE
                                    │
                                    ▼
                         12-VARIABLE QUBO MODEL
                                    │
                                    ▼
                         QUBO ──→ ISING MAPPING
                                    │
                                    ▼
                       12-QUBIT QAOA (Qiskit Aer)
                                    │
                                    ▼
                          CANDIDATE VALIDATION
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
             VALID CANDIDATE                  TIMEOUT / INVALID
                  │                                   │
                  │                                   ▼
                  │                          SIMULATED ANNEALING
                  │                         (dwave-neal Fallback)
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    │
                                    ▼
                            NORMAL SIGNAL PLAN
                       {I1: d1, I2: d2, I3: d3, I4: d4}
                                    │
                                    ▼
                     MICROSCOPIC TRAFFIC SIMULATOR
                     (Discrete-Time t = 0..300s)
                                    │
                                    ▼
                    DYNAMIC EMERGENCY CORRIDOR OVERLAY
                     (Preemption: I2 ──→ I3 ──→ I4)
                                    │
                                    ▼
                   INTEGRATION TELEMETRY & EVENT LOG
                      (QuantumFlowRunResult / JSON)
```

---

## 4. QUBO Formulation

The total objective Hamiltonian is expressed as:

$$H_{\text{total}} = H_{\text{onehot}} + H_{\text{wait}} + H_{\text{capacity}} - H_{\text{throughput}} + H_{\text{coupling}} + H_{\text{emergency}}$$

### Mathematical Components

1. **One-Hot Constraint**:
   Ensures exactly one green duration is selected per intersection:
   $$H_{\text{onehot}} = A \sum_{i} \left(\sum_{t \in \{15, 30, 45\}} x_{i,t} - 1\right)^2$$

2. **Waiting Time Penalty**:
   Penalizes insufficient green time for waiting queues ($q_i$):
   $$H_{\text{wait}} = B \sum_{i, t} \left(\frac{q_i}{t}\right) x_{i,t}$$

3. **Capacity Pressure Penalty**:
   Penalizes short green times when density $d_i$ exceeds threshold (0.7):
   $$H_{\text{capacity}} = C \sum_{i, t} \max(0, d_i - 0.7)(45 - t) x_{i,t}$$

4. **Throughput Reward**:
   Rewards vehicle clearance capacity with service rate $\mu$:
   $$H_{\text{throughput}} = E \sum_{i, t} \min(q_i, \mu t) x_{i,t} \quad \text{(subtracted from energy)}$$

5. **Inter-Intersection Coupling**:
   Penalizes upstream discharge into congested, short-green downstream nodes ($i \to j$):
   $$H_{\text{coupling}} = D \sum_{(i \to j), t_i, t_j} \left(\frac{t_i}{45}\right) \left(\frac{q_j}{C_j}\right) \left(1 - \frac{t_j}{45}\right) x_{i,t_i} x_{j,t_j}$$

6. **Emergency Route Constraint**:
   Penalizes non-maximum green allocation along designated emergency corridors:
   $$H_{\text{emergency}} = F \sum_{k \in \text{route}} (1 - x_{k,\text{forced}})$$

### Matrix Convention
The implementation follows an upper-triangular QUBO storage standard:
$$E(x) = x^T Q x + \text{offset}$$
where $Q[i, j]$ for $i < j$ contains the complete interaction coefficient $x_i x_j$ with zero lower-triangular entries ($Q[j, i] = 0$ for $j > i$).

---

## 5. Canonical Variables

The system operates on 12 canonical binary decision variables ($x_k \in \{0, 1\}$):

| Variable Index | Variable Name | Intersection | Duration ($t$) |
| :---: | :---: | :---: | :---: |
| **0** | `I1_15` | I1 | 15s |
| **1** | `I1_30` | I1 | 30s |
| **2** | `I1_45` | I1 | 45s |
| **3** | `I2_15` | I2 | 15s |
| **4** | `I2_30` | I2 | 30s |
| **5** | `I2_45` | I2 | 45s |
| **6** | `I3_15` | I3 | 15s |
| **7** | `I3_30` | I3 | 30s |
| **8** | `I3_45` | I3 | 45s |
| **9** | `I4_15` | I4 | 15s |
| **10** | `I4_30` | I4 | 30s |
| **11** | `I4_45` | I4 | 45s |

### One-Hot Decoding
A valid binary state contains exactly one active bit in each of the four 3-variable blocks, spanning a feasible subspace of $3^4 = 81$ valid configurations out of $2^{12} = 4096$ total states.

---

## 6. Quantum Implementation

- **QUBO to Ising Mapping**: Converts binary variables $x_i \in \{0, 1\}$ to Pauli-Z spin operators $Z_i \in \{+1, -1\}$ via algebraic substitution $x_i = \frac{1 - Z_i}{2}$.
- **Circuit Architecture**: 12 qubits initialized in uniform superposition $|+\rangle^{\otimes 12}$.
- **Parameterized Alternating Layers**:
  - Phase separator: $U(H_C, \gamma) = e^{-i \gamma H_C}$
  - Mixer operator: $U(H_M, \beta) = e^{-i \beta \sum_i X_i}$
- **Execution & Optimization**: Simulated on Qiskit Aer statevector/qasm simulator with classical parameter optimization using COBYLA.
- **Candidate Evaluation**: Candidate states measured across measurement shots (default 1024) are decoded and ranked by exact QUBO energy $E(x)$. The candidate with the lowest exact QUBO energy is selected (most frequent measurement is not assumed optimal).

---

## 7. Classical Fallback & Hybrid Orchestration

The `HybridController` implements a deterministic reliability policy:

1. **Primary Execution**: QAOA is executed with configurable parameters ($p=1$, maxiter=30, shots=1024, timeout=60s).
2. **Operational Validation**: The returned candidate is validated for:
   - Execution completion without exception or timeout.
   - One-hot feasibility (exactly one active duration per intersection).
   - Finite QUBO energy evaluation.
3. **Fallback Condition**: Classical Simulated Annealing (`dwave-neal`) is invoked on the **exact same QUBO model** only when operational invalidity or failure occurs.
4. **Suboptimal Acceptance**: A valid, feasible QAOA candidate that does not achieve the theoretical global minimum is accepted as a valid heuristic solution and does **not** trigger classical fallback.

---

## 8. Dynamic Emergency Green Corridor

The runtime emergency system dynamically preempts traffic signals for authorized emergency vehicles traveling along the designated corridor:

$$\text{Route: } \text{I2} \longrightarrow \text{I3} \longrightarrow \text{I4}$$

### Lifecycle Progression
1. **Emergency Detection**: Senses emergency vehicle entry at origin intersection (`I2`).
2. **Progressive Preemption**: Actively forces the approach signal to `PREEMPT_ACTIVE` (forced green).
3. **Downstream Lookahead Preparation**: Transitions upcoming downstream intersections to `PREPARE` mode within a configurable lookahead horizon.
4. **Clean Localized Release**: Releases cleared intersections back to normal control as the emergency vehicle moves downstream.
5. **Automatic Recovery**: Seamlessly restores cyclic signal timing on all nodes upon emergency vehicle completion.
6. **Telemetry & Event Log**: Logs every state transition with discrete second timestamps and details.

---

## 9. Traffic Simulator

The platform includes a lightweight, deterministic discrete-time microscopic traffic simulation engine:

- **Time Step**: Discrete 1-second ticks ($\Delta t = 1\text{ s}$).
- **Queue Progression**: FIFO queue servicing based on intersection green phases and saturation service rates ($\mu = 1.0\text{ veh/s}$).
- **Arrival Modeling**: Deterministic Poisson arrivals parameterized by entry arrival rates and random seeds.
- **Pipeline Transit**: Models vehicle transit delays between adjacent intersections ($\tau = 2\text{ s}$).
- **Signal Control**: Cyclic green/red allocation driven by the assigned normal signal plan.

---

## 10. Metrics & Telemetry

The integration layer emits comprehensive, JSON-serializable performance metrics:

### Traffic Performance
- `total_waiting_time`: Cumulative stationary queue seconds across all vehicles.
- `average_waiting_time`: Mean waiting time per generated vehicle.
- `max_queue`: Peak queue length observed at any intersection.
- `average_queue`: Mean network queue size across the simulation duration.
- `throughput`: Total vehicles successfully reaching network destination.
- `normal_vehicles_waiting_time`: Cumulative waiting time of non-emergency vehicles.

### Emergency Telemetry
- `emergency_response_time`: Total travel seconds from vehicle injection to exit.
- `emergency_waiting_time`: Stationary queue delay experienced by the emergency vehicle.
- `emergency_completed`: Boolean flag indicating destination completion.
- `emergency_detected_time` & `emergency_completed_time`: Timestamps of corridor entry and exit.
- `emergency_intersections_cleared`: Count of corridor nodes cleared.
- `emergency_preemption_count`: Total preemption activations executed.
- `corridor_event_log`: Structured chronological audit trail of all corridor events.

---

## 11. Benchmarking & Comparative Evaluation

The repository includes a controlled evaluation framework benchmarking four distinct controller strategies under identical traffic scenarios:

1. **HybridController**: QAOA primary optimizer with automatic classical SA fallback.
2. **SimulatedAnnealingController**: Classical simulated annealing baseline (`dwave-neal`).
3. **FixedTimeController**: Deterministic static signal plan (e.g., 30s green across all nodes).
4. **RuleBasedController**: Actuated heuristic controller mapping local queue lengths and densities to durations.

Ground truth optimality on the 12-variable model is validated via exhaustive enumeration across all $2^{12} = 4096$ states.

> [!IMPORTANT]
> All comparative evaluations report strictly objective arithmetic differences ($\Delta = \text{QuantumFlow} - \text{Baseline}$) without subjective rankings or claims of superiority.

---

## 12. Validation & Testing

The repository contains extensive unit tests across 12 test suites covering QUBO formulation, Ising conversion, QAOA execution, classical SA, hybrid fallback, traffic simulation, emergency preemption, and JSON serialization.

### Running Test Suite

```bash
python -m pytest -q
```

### Running Canonical Demonstration

```bash
python examples/run_quantumflow_demo.py
```

---

## 13. Installation & Setup

### Prerequisites
- Python 3.10 to 3.13 (verified on 3.13.15 with the pinned `requirements.txt`; **Python 3.14 is not supported** - the pinned `numpy==2.2.6` has no working 3.14 build)
- Git

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/gee-46/TARS-021-Quantexa-project.git
cd TARS-021-Quantexa-project

# 2. Create and activate a virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt      # includes streamlit for the dashboard
# Optional, only for the unverified real-IBM-hardware path:
# pip install -r requirements-ibm.txt

# 4. Run the tests (collects tests/ only, see pytest.ini)
python -m pytest -q
```

---

## 14. Running the Demonstration

Execute the canonical end-to-end integration demo comparing QuantumFlow dynamic corridor against the baseline:

```bash
python examples/run_quantumflow_demo.py
```

### Example Console Output
_Captured from an actual run (Python 3.13.15, pinned requirements, seed 42). The optimisation runtime line varies from run to run; all other values are deterministic for the seed._

```
==================================================
QUANTUMFLOW END-TO-END DEMO
==================================================
Scenario ID: canonical_phase15_demo
Simulation Duration: 300s | Network: I1 -> I2 -> I3 -> I4
Random Seed: 42
--------------------------------------------------

Executing RUN A: Hybrid Controller (Corridor ENABLED)...
Executing RUN B: Hybrid Controller (Corridor DISABLED - Baseline)...

==================================================
RUN A TELEMETRY: QUANTUMFLOW DYNAMIC CORRIDOR
==================================================

NORMAL SIGNAL PLAN:
  I1: 45s green (60s cycle)
  I2: 45s green (60s cycle)
  I3: 45s green (60s cycle)
  I4: 45s green (60s cycle)
Optimization Solver:     qaoa
Optimization Status:     success
Optimization Energy:     -43.0000
Optimization Runtime:    2.5901s
Fallback Used:           False

EMERGENCY TELEMETRY:
Emergency Present:       True
Emergency Detected:      t=20s
Corridor Activated:      t=20s
Emergency Completed:     t=68s
Emergency Response Time: 48.0s
Emergency Waiting Time:  44.0s
Intersections Cleared:   3
Preemption Count:        3
Recovery Completed:      True

TRAFFIC PERFORMANCE:
Throughput:              234 vehicles
Average Waiting Time:    25.59s
Max Queue:               19 vehicles
Normal Vehicle Wait:     6609.0s

==================================================
BASELINE VS DYNAMIC CORRIDOR DELTAS (Corridor - Baseline)
==================================================
Emergency Response Delta: -9.0s
Emergency Waiting Delta:  -9.0s
Normal Waiting Delta:     -2202.0s
Average Waiting Delta:    -8.50s
Throughput Delta:         +9 vehicles
Max Queue Delta:          -6 vehicles
Preemption Delta:         +3
Energy Delta:             +0.0000
==================================================
```

---

## 15. Project Structure

```
TARS-021-Quantexa-project/
├── README.md
├── requirements.txt / requirements-ibm.txt   # Pinned deps (Python 3.10-3.13) / optional IBM runtime
├── pytest.ini                                # Collects tests/ only
├── main.py                                   # CLI demo (python main.py) or --gui for Streamlit
├── api_server.py                             # FastAPI service used by the React control center
├── streamlit_app.py, dashboard.py            # Streamlit loader + command-center dashboard
├── docs/                                     # Architecture, QUBO/Ising math, benchmark method, limitations, upgrade status
├── examples/                                 # run_quantumflow_demo.py, generate_results.py
├── results/                                  # Regenerated benchmark JSON (simulator only) + provenance README
├── optimization/                             # QUBO builder, Ising mapping, QAOA/SA/Greedy solvers, arbiter,
│                                             #   emergency-conflict QUBO, Pareto, hardware (ideal/noisy/IBM opt-in)
├── simulation/                               # Microscopic simulator, adaptive & emergency controllers, scenarios,
│                                             #   metrics, emissions, Belagavi-inspired corridor data, scenario registry
├── tests/                                    # pytest suite (solvers, simulator, controllers, API)
├── src/, public/, index.html, vite.config.js # React control center (Vite): pages, components, services
└── frontend/webthreads/                      # Streamlit number-glitch loader component
```

---

## 16. Reproducibility & Environment

The backend validation was established on the following verified environment:

- **Python**: `3.13.x` (supported range 3.10-3.13; 3.14 is not supported by the pinned NumPy)
- **Qiskit**: `2.5.2`
- **Qiskit Aer**: `0.17.2`
- **dwave-neal**: `0.6.0`
- **dimod**: `0.12.22`
- **NumPy**: `2.2.6`
- **SciPy**: `1.17.1`
- **Pytest**: `9.1.1`
- **Random Seeds**: Controlled deterministic runs using `seed=42`.

---

## 17. Scientific Limitations & Boundary Conditions

1. **Simulation vs. Real-World Hardware**: QAOA is evaluated using Qiskit Aer statevector simulation on classical CPUs, not physical quantum processing units (QPUs).
2. **Problem Scale**: The problem size is fixed at 12 binary variables across 4 intersections.
3. **No Quantum Advantage**: QAOA serves as a mathematical optimization proof-of-concept; no speedup or advantage over classical heuristics is claimed.
4. **Heuristic Sampling**: QAOA sampling may select feasible suboptimal candidates rather than the exact global minimum.
5. **Simplified Microscopic Model**: The discrete-time simulator is designed for objective comparative timing evaluation and does not model lane-changing, pedestrian phases, or vehicle kinematics.
6. **Classical Emergency Preemption**: The dynamic emergency green corridor is managed entirely by classical real-time control logic.

---

## 18. Quantexa Hackathon Project

Developed as part of the Quantexa Hackathon by the TARS-021 engineering team.
- **Repository**: [gee-46/TARS-021-Quantexa-project](https://github.com/gee-46/TARS-021-Quantexa-project)
- **Team**: TARS-021

---

## 19. Web Dashboard Quickstart

### Python / Streamlit Command Center
```bash
streamlit run streamlit_app.py
```
After the loader, the dashboard has tabs for adaptive control, people & fairness, multi-ambulance conflicts (QAOA vs SA vs Greedy), the solver arbiter, the Pareto slider, a simulator-vs-IBM-hardware comparison (hardware is opt-in) and a schematic Belagavi digital twin.

### React Control Center (QuantumForce UI + Python API)
```bash
pip install -r requirements.txt
npm ci && npm run build
python -m uvicorn api_server:app --port 8000     # UI + API at http://127.0.0.1:8000
# development with hot reload: npm run dev   (proxies /api to 127.0.0.1:8000)
```
The React app is a client of `api_server.py`, which returns results computed by the simulator, QUBO builder and solvers; it contains no hard-coded metrics. See [docs/frontend_integration.md](docs/frontend_integration.md) for the audit of the merged frontend, what was changed, and limitations.

---

## 20. Upgrade Status, Results and Honest Scope

See [docs/upgrade_status.md](docs/upgrade_status.md) for the eight upgrades, the defects fixed along the way, what the results do and do not show, and known limitations.

- **QAOA runs on the local Qiskit Aer simulator.** Ideal-vs-noisy *simulation* is available (generic noise model, not a calibrated device).
- **Real IBM hardware is optional future validation.** The runtime path (`optimization/ibm_hardware.py`) is implemented and documented but **unverified** until a run on an actual IBM account/device succeeds. No hardware timings, fidelities or results exist in this repository.
- **The Belagavi content is a "Belagavi-inspired corridor", not a digital twin.** The four junction locations and the road geometry between them are real OpenStreetMap data (`simulation/data/belagavi_geo.json`, refreshed with `examples/fetch_belagavi_geo.py`); which junctions form the corridor, signal timings and all traffic volumes are assumed. Tilakwadi is a suburb centroid.
- **No quantum advantage is claimed.**
- **Results:** `results/benchmark_results*.json` are regenerated with `python examples/generate_results.py` (see [results/README.md](results/README.md)); all are simulator results.
