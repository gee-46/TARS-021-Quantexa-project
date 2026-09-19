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
- Python 3.10 to 3.13
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
pip install -r requirements.txt
```

---

## 14. Running the Demonstration

Execute the canonical end-to-end integration demo comparing QuantumFlow dynamic corridor against the baseline:

```bash
python examples/run_quantumflow_demo.py
```

### Example Console Output
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
  I4: 30s green (60s cycle)
Optimization Solver:     qaoa
Optimization Status:     success
Optimization Energy:     -42.5333
Optimization Runtime:    1.4690s
Fallback Used:           False

EMERGENCY TELEMETRY:
Emergency Present:       True
Emergency Detected:      t=20s
Corridor Activated:      t=20s
Emergency Completed:     t=83s
Emergency Response Time: 63.0s
Emergency Waiting Time:  59.0s
Intersections Cleared:   3
Preemption Count:        3
Recovery Completed:      True

TRAFFIC PERFORMANCE:
Throughput:              159 vehicles
Average Waiting Time:    66.84s
Max Queue:               81 vehicles
Normal Vehicle Wait:     17319.0s

==================================================
BASELINE VS DYNAMIC CORRIDOR DELTAS (Corridor - Baseline)
==================================================
Emergency Response Delta: -39.0s
Emergency Waiting Delta:  -39.0s
Normal Waiting Delta:     -2172.0s
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
├── README.md                           # Comprehensive documentation & research summary
├── requirements.txt                    # Pinned core dependency specifications
├── docs/
│   ├── ising_mapping.md                # QUBO to Ising transformation proofs & verification
│   ├── integration_contract.md         # Data schemas, backend API, & serialization contract
│   └── final_validation.md             # Complete end-to-end regression & validation report
├── docs/
│   ├── architecture.md                 # Full system architecture and end-to-end pipeline
│   ├── objective_design.md             # QUBO mathematical formulations and penalties
│   ├── multi_emergency.md              # Multi-vehicle emergency arbitration and conflict QUBO
│   ├── benchmark_methodology.md        # Reproducible benchmarking and evaluation protocol
│   ├── limitations.md                  # Modeling assumptions and quantum computing disclaimers
│   ├── upgrade_audit.md                # Phase-by-phase hardening and upgrade audit
│   └── integration_contract.md         # Telemetry schemas and serialization contracts
├── examples/
│   └── run_quantumflow_demo.py         # Reproducible canonical demonstration runner
├── optimization/
│   ├── __init__.py                     # Module exports
│   ├── variables.py                    # Canonical 12-variable indexing & topology mappings
│   ├── traffic_objectives.py           # Objective function components, people-weighting & Jain fairness
│   ├── onehot.py                       # One-hot penalty formulation
│   ├── coupling.py                     # Inter-intersection coupling penalties
│   ├── emergency.py                    # Emergency corridor constraints
│   ├── emergency_conflict.py           # Multi-emergency conflict QUBO & priority sequencing
│   ├── solver_arbiter.py               # Objective comparative benchmark (QAOA vs SA vs Greedy)
│   ├── pareto.py                       # Multi-objective Pareto trade-off curve evaluator (lambda sweep)
│   ├── qubo_model.py                   # Upper-triangular QUBOModel data structure
│   ├── qubo_builder.py                 # QUBO matrix assembly & parameter weighting
│   ├── ising_converter.py              # Exact QUBO to Ising Hamiltonian transformation
│   ├── enumeration.py                  # Exhaustive 4096-state ground truth solver & normalized metrics
│   ├── qaoa_solver.py                  # Parameterized QAOA ansatz & Aer execution
│   ├── production_qaoa.py              # Production 12-qubit QAOA solver with timeout protection
│   ├── sa_solver.py                    # Classical Simulated Annealing baseline (dwave-neal)
│   ├── decoder.py                      # Bitstring decoding & feasibility validation
│   ├── hybrid_solver.py                # QAOA primary solver with automated SA fallback
│   ├── controllers.py                  # Standardized traffic controller adapters
│   ├── benchmark_metrics.py            # TrialResult and telemetry containers
│   └── benchmark.py                    # Controlled multi-scenario benchmark runner (Scenarios A-G)
├── simulation/
│   ├── __init__.py                     # Module exports
│   ├── models.py                       # Microscopic Vehicle, VehicleTypeConfig, and SignalState
│   ├── scenario.py                     # SimulationScenario & canonical factory (Scenarios A-G)
│   ├── adaptive_controller.py          # Closed-loop rolling horizon replanning controller
│   ├── emergency_events.py             # Event types, modes, and EmergencyEvent records
│   ├── emergency_controller.py         # Dynamic route-aware multi-emergency green corridor controller
│   ├── emissions.py                    # Idling vehicle delay, fuel burn, and CO2 emissions model
│   ├── engine.py                       # Discrete-time microscopic TrafficSimulator
│   ├── metrics.py                      # SimulationMetrics calculations & Jain fairness
│   └── integration.py                  # End-to-end pipeline runner & JSON serialization
└── tests/
    ├── __init__.py
    ├── test_qubo.py                    # QUBO component & assembly unit tests
    ├── test_ising.py                   # QUBO-Ising exact equivalence verification
    ├── test_qaoa.py                    # Small-scale QAOA circuit verification
    ├── test_production_qaoa.py         # 12-qubit QAOA production solver tests
    ├── test_sa_solver.py               # Simulated annealing baseline tests
    ├── test_decoder.py                 # One-hot and emergency feasibility tests
    ├── test_hybrid_solver.py           # Hybrid fallback and timeout tests
    ├── test_adaptive_controller.py     # Rolling horizon adaptive replanning tests
    ├── test_emergency_conflict.py      # Multi-emergency conflict QUBO tests
    ├── test_solver_arbiter.py          # QAOA vs SA vs Greedy arbiter tests
    ├── test_people_metrics.py          # Passenger occupancy & person-delay tests
    ├── test_fairness.py                # Jain fairness & starvation penalty tests
    ├── test_emissions.py               # Deterministic fuel & CO2 emissions tests
    ├── test_pareto.py                  # Pareto multi-objective lambda sweep tests
    ├── test_benchmark.py               # Benchmark framework tests
    ├── test_simulation.py              # Microscopic traffic simulator tests
    ├── test_emergency_corridor.py      # Dynamic green corridor & recovery tests
    └── test_integration.py             # End-to-end integration & serialization tests
```

---

## 16. Reproducibility & Environment

The backend validation was established on the following verified environment:

- **Python**: `3.13.5` (compatible with Python $\ge$ 3.10)
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

### React / Vite Application
```bash
npm install
npm run dev
```

---

## 20. Upgrade Status

See [docs/upgrade_status.md](docs/upgrade_status.md) for the eight upgrades (adaptive control, person-weighted objective, fairness, multi-ambulance conflict QUBO, solver arbiter, Pareto slider, IBM hardware path, Belagavi twin), the defects fixed along the way, what the results do and do not show, and known limitations. The Belagavi twin is a labelled simulation abstraction, and the IBM-hardware branch has not been run on a real device in this repository.
