# QuantumFlow Benchmark Methodology & Evaluation Framework

## 1. Scientific Principles & Fairness

QuantumFlow implements a strictly controlled, reproducible benchmark methodology:
1. **Identical Test Conditions**: Every evaluated algorithm (Fixed-Time, Rule-Based, Greedy Local Search, Simulated Annealing, QAOA, Hybrid, and Adaptive Hybrid) solves the identical traffic demand instance under identical random seeds.
2. **Unmanipulated Objective Scoring**: Candidate solutions are evaluated strictly on their exact QUBO objective energy $E(x) = x^T Q x + \text{offset}$ and microscopic traffic metrics.
3. **No Artificial Quantum Superiority**: QAOA is benchmarked transparently against classical heuristics. If Simulated Annealing or Greedy finds a lower-energy configuration faster, that delta is reported factually.
4. **Separation of Concerns**: Optimization metrics (energy, runtime, feasibility) are decoupled from simulation metrics (throughput, delay, fairness, CO2).

---

## 2. Benchmark Scenarios (A through G)

| Scenario ID | Name | Description | Key Characteristic |
| :--- | :--- | :--- | :--- |
| **Scenario A** | Balanced Traffic | Symmetric arrival rates (0.25 veh/s) across all nodes | Uniform baseline flow |
| **Scenario B** | Heavy Congestion | High saturation demand (0.45-0.60 veh/s), initial queues | Tests queue dissipation capacity |
| **Scenario C** | Bus Transit Corridor | High transit frequency with 35-passenger buses on I1/I2 | Evaluates person-weighted delay minimization |
| **Scenario D** | Single Emergency | Ambulance traversing full arterial I1 -> I4 | Measures preemption & clearance efficiency |
| **Scenario E** | Two Conflicting Emergencies | Opposing corridors contending for intersection I3 | Evaluates multi-emergency arbitration QUBO |
| **Scenario F** | Three Emergency Conflict | 3 simultaneous vehicles contending at central junction | Tests complex multi-vehicle sequencing |
| **Scenario G** | High-Demand Adaptive Traffic | Dynamic continuous arrival flow over 300s | Tests closed-loop rolling-horizon replanning |

---

## 3. Evaluated Metrics Contract

- **Optimization**:
  - QUBO Energy $E(x)$
  - Wall-clock Solver Runtime (s)
  - Feasibility (One-Hot validity, Emergency validity)
  - Optimality Gap $\Delta E = E_{\text{solver}} - E_{\text{opt}}$
- **Microscopic Traffic**:
  - Total Vehicle Throughput
  - Average & Maximum Waiting Delay (s)
  - Total Person-Seconds Delay
  - Maximum Queue Length
- **Fairness & Equity**:
  - Jain's Fairness Index $J(x) = \frac{(\sum x_i)^2}{n \sum x_i^2}$
  - Starvation Violations (delays exceeding $W_{\text{cap}}$)
  - Max Approach Delay
- **Emergency Operations**:
  - Emergency Response Travel Time (s)
  - Emergency Queuing Delay (s)
  - Preemption Count & Intersection Clearances
- **Environmental Impact**:
  - Cumulative Idling Vehicle Seconds
  - Estimated Fuel Consumption (Liters)
  - Estimated $\text{CO}_2$ Emissions (kg)
