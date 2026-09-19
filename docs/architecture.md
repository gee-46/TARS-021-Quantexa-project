# QuantumFlow System Architecture

## 1. Overview & Pipeline

QuantumFlow is an adaptive, people-aware, fairness-constrained, multi-emergency hybrid quantum-classical traffic signal optimization platform. It couples a mathematically rigorous 12-variable Quadratic Unconstrained Binary Optimization (QUBO) formulation solved via gate-level Quantum Approximate Optimization Algorithm (QAOA) on Qiskit Aer (with classical Simulated Annealing fallback) to a second-by-second discrete microscopic traffic simulation.

```
LIVE TRAFFIC STATE (Queues, Densities, Occupancies, Delay)
        ↓
PERSON / VEHICLE / MULTI-EMERGENCY STATE
        ↓
ADAPTIVE STATE BUILDER (Rolling-Horizon Snapshot)
        ↓
CANONICAL QUBO FORMULATION (12 Binary Decision Variables)
        ↓
QAOA SOLVER (Parameterized Qiskit Aer Gate Simulation)
        ↓ (Validation Gate: One-Hot & Emergency Validity)
SA FALLBACK (dwave-neal Classical Thermal Baseline)
        ↓
SOLVER ARBITER (Side-by-Side QAOA vs SA vs Greedy Comparison)
        ↓
SIGNAL PLAN DECODER ({"I1": 15/30/45, ...})
        ↓
MICROSCOPIC TRAFFIC SIMULATION (Discrete 4-Intersection Grid)
        ↓
MULTI-EMERGENCY CONFLICT ARBITRATOR (Dynamic Preemption & QUBO Sequencing)
        ↓
TELEMETRY & ENVIRONMENTAL METRICS (Person Delay, Jain Fairness, Fuel, CO2)
        ↓
STREAMLIT COMMAND CENTER DASHBOARD
```

---

## 2. Core Components

### 2.1 Optimization Layer (`optimization/`)
- **`variables.py`**: Authoritative indexing of 12 binary variables ($x_{i, t} \in \{0, 1\}$ for $i \in \{I1, I2, I3, I4\}$, $t \in \{15, 30, 45\}$).
- **`qubo_model.py`**: Upper-triangular matrix convention ($E(x) = x^T Q x + \text{offset}$).
- **`qubo_builder.py`**: Master QUBO synthesis extending one-hot penalties, local queues, network coupling, emergency holds, people-weighting, and starvation penalties.
- **`production_qaoa.py`**: 12-qubit parameterized QAOA on Qiskit Aer with COBYLA classical optimization.
- **`sa_solver.py`**: D-Wave Neal simulated annealing solver consuming the identical upper-triangular QUBO model.
- **`hybrid_solver.py`**: Operational controller executing QAOA first and falling back to SA on failure or constraint violation.
- **`solver_arbiter.py`**: Multi-solver comparative benchmark comparing QAOA, SA, and Greedy local search on identical QUBOs without score manipulation.
- **`emergency_conflict.py`**: Dedicated QUBO formulation and scheduler for resolving multi-emergency junction contention.
- **`pareto.py`**: Multi-objective Pareto trade-off curve evaluator across emergency prioritization parameter $\lambda \in [0.0, 1.0]$.
- **`enumeration.py`**: Exact ground-truth enumeration for 12 variables ($2^{12} = 4096$ states) with normalized optimality metrics.

### 2.2 Microscopic Simulation Layer (`simulation/`)
- **`models.py`**: Vehicle entity tracking route progress, arrival time, waiting time, passenger count, and `VehicleTypeConfig` (car, bus, motorcycle, truck, emergency).
- **`engine.py`**: Discrete-time second-by-second microscopic traffic simulation engine tracking individual queues, transit pipelines, green/red signal phases, and preemption.
- **`adaptive_controller.py`**: Closed-loop rolling horizon replanning at cycle boundaries ($t=0, 60, 120, 180, 240$) without state or RNG resets.
- **`emergency_controller.py`**: Multi-vehicle progressive green corridor preemption and conflict-free release.
- **`emissions.py`**: Deterministic fuel consumption ($0.7\text{ L/veh-hr}$) and carbon emissions ($2.31\text{ kg CO}_2\text{/L}$) modeling from cumulative idle delay.
- **`metrics.py`**: Standardized metrics recording throughput, vehicle delay, person delay, Jain fairness index, starvation violations, and emissions.
- **`scenario.py`**: Declarative scenario specifications including canonical Scenarios A through G.

---

## 3. Invariant Safety & Mathematical Rules
1. **Single Source of Truth**: Exactly one 12-variable QUBO model.
2. **Deterministic Evaluation**: Replicable behavior governed by explicit PRNG seeds.
3. **No Advantage Claims**: Objective evaluation on simulated quantum backends.
4. **Clean Boundary Transitions**: Signal plans applied only at cycle boundaries without mid-cycle jumps.
