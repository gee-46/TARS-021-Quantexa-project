# QuantumFlow End-to-End Backend Integration Contract

## 1. Architectural Pipeline & Boundary

QuantumFlow provides an end-to-end multi-intersection traffic optimization and dynamic emergency preemption system. The backend architecture follows a strict separation of concerns across optimization, simulation, and emergency control:

```
┌──────────────────────────────────────────────────────────┐
│ 1. OFFLINE NORMAL OPTIMIZATION                            │
│    QUBO Model -> QAOA (Primary) -> SA (Fallback)         │
│    Output: Normal Signal Plan {I1: d1, I2: d2, ...}      │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 2. DISCRETE-TIME TRAFFIC SIMULATOR                       │
│    Microscopic Second-by-Second Network Progression      │
│    - Deterministic Poisson Arrivals (seed-controlled)    │
│    - Intersection Queue Servicing (FIFO)                 │
│    - Inter-Intersection Transit Pipelines                │
│    ┌────────────────────────────────────────────────┐    │
│    │ DYNAMIC EMERGENCY CORRIDOR OVERLAY             │    │
│    │ - Emergency Detection (t=20s, I2->I3->I4)      │    │
│    │ - Progressive Preemption (Forced Green Wave)   │    │
│    │ - Downstream Lookahead Preparation             │    │
│    │ - Clean Intersection Release & Normal Recovery │    │
│    └────────────────────────────────────────────────┘    │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 3. STRUCTURED INTEGRATION TELEMETRY & SERIALIZATION      │
│    QuantumFlowRunResult / RunComparisonResult            │
│    - Pure Python JSON-safe serialization (.to_dict())    │
│    - Objective arithmetic deltas (compare_runs)          │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Guarantees

1. **Role of Quantum Algorithm (QAOA)**:
   - QAOA is an offline mathematical optimization component that solves for optimal static green duration allocations under normal traffic distribution.
   - QAOA does **not** act as a real-time reactive controller.
   - QAOA does **not** solve the real-time emergency routing during live traffic simulation.

2. **Automated Classical Fallback (SA)**:
   - Classical Simulated Annealing (`dwave-neal`) serves as the operational fallback.
   - Fallback triggers only upon operational necessity: algorithm failure, circuit timeout, or violation of one-hot validity constraints.
   - QAOA finding a valid suboptimal solution is accepted as a valid heuristic candidate and does not trigger fallback.

3. **Separation of Normal Optimization & Emergency Control**:
   - The offline optimizer solves the baseline network demands to produce `normal_signal_plan`.
   - At runtime during simulation, the `EmergencyCorridorController` dynamically preempts signals along active emergency vehicle routes (`PREEMPT_ACTIVE` forced green).
   - Downstream intersections enter `PREPARE` mode via lookahead timers.
   - Once the emergency vehicle clears an intersection or finishes transit, the intersection releases back to `NORMAL` cyclic control.

4. **Objective Scientific Measurement**:
   - No claim of quantum speedup, quantum supremacy, or quantum advantage is made.
   - All performance values are calculated from measured microscopic simulation runs.
   - Comparative evaluations between baseline and QuantumFlow use strictly objective arithmetic deltas (`quantumflow - baseline`) without value judgments or declaring "winners".

---

## 3. Python Integration API

### `run_quantumflow_demo`

```python
from simulation.integration import run_quantumflow_demo, create_canonical_demo_scenario

# Run canonical demonstration with dynamic corridor enabled
result = run_quantumflow_demo(
    scenario=None,  # Defaults to canonical Phase 15 scenario
    seed=42,
    enable_emergency_corridor=True,
    controller="hybrid",
    qaoa_p=1,
    qaoa_maxiter=30,
    qaoa_shots=1024,
)
```

### `compare_runs`

```python
from simulation.integration import run_quantumflow_demo, compare_runs

# Run baseline (corridor disabled)
baseline = run_quantumflow_demo(seed=42, enable_emergency_corridor=False, controller="hybrid")

# Run QuantumFlow (corridor enabled)
corridor = run_quantumflow_demo(seed=42, enable_emergency_corridor=True, controller="hybrid")

# Compute arithmetic deltas (corridor - baseline)
deltas = compare_runs(baseline=baseline, quantumflow=corridor)
print(deltas.to_dict())
```

---

## 4. `QuantumFlowRunResult` Schema & Serialization

The `QuantumFlowRunResult.to_dict()` method guarantees pure JSON-safe primitives (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`).

### Data Schema

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `run_id` | `str` | Unique execution identifier |
| `scenario_id` | `str` | Scenario identifier |
| `seed` | `int` | Random seed used for generation and simulation |
| `normal_controller` | `str` | Controller adapter used (`hybrid_quantumflow`, `classical_sa`, etc.) |
| `normal_signal_plan` | `Dict[str, int]` | Assigned green durations per intersection (e.g. `{"I1": 45, "I2": 45, "I3": 45, "I4": 45}`) |
| `optimization_status` | `str` | Optimizer outcome status (`"success"` or `"failed"`) |
| `optimization_solver` | `str` | Primary solver executing decision (`"qaoa"`, `"sa"`, `"fixed"`, `"rule_based"`) |
| `optimization_energy` | `float` | Exact QUBO energy of the selected normal signal plan |
| `optimization_runtime` | `float` | Wall-clock seconds spent in optimization |
| `optimization_fallback_used` | `bool` | `True` if classical SA fallback was triggered |
| `optimization_fallback_reason` | `Optional[str]` | Detailed reason if fallback occurred |
| `canonical_bitstring` | `Optional[str]` | 12-bit binary string representation (`x_0...x_11`) |
| `binary_vector` | `Optional[List[int]]` | 12-element binary list in $\{0, 1\}^{12}$ |
| `onehot_valid` | `bool` | `True` if exactly one duration is active per intersection |
| `emergency_valid` | `bool` | `True` if static emergency constraint was satisfied |
| `simulation_duration` | `int` | Total simulation horizon in seconds (e.g. `300`) |
| `throughput` | `int` | Total vehicles completed and exited the network |
| `average_waiting_time` | `float` | Mean seconds spent waiting across all vehicles |
| `max_queue` | `int` | Peak queue length observed across all intersections |
| `average_queue` | `float` | Mean network queue size over time |
| `vehicles_generated` | `int` | Total vehicles injected into the network |
| `vehicles_completed` | `int` | Total vehicles reaching destination |
| `normal_vehicles_waiting_time` | `float` | Cumulative waiting time of non-emergency vehicles |
| `emergency_present` | `bool` | `True` if emergency vehicle was scheduled in scenario |
| `emergency_corridor_enabled` | `bool` | `True` if dynamic corridor preemption was active |
| `emergency_detected_time` | `Optional[int]` | Second $t$ when emergency vehicle was detected |
| `emergency_corridor_activated_time` | `Optional[int]` | Second $t$ when dynamic corridor was engaged |
| `emergency_completed_time` | `Optional[int]` | Second $t$ when emergency vehicle reached destination |
| `emergency_response_time` | `Optional[float]` | Total travel duration (seconds) from arrival to exit |
| `emergency_waiting_time` | `Optional[float]` | Seconds emergency vehicle spent stationary in queue |
| `emergency_travel_time` | `Optional[float]` | Total seconds emergency vehicle spent in network |
| `emergency_completed` | `bool` | `True` if emergency vehicle reached destination |
| `emergency_intersections_cleared` | `int` | Number of route intersections traversed and cleared |
| `emergency_preemption_count` | `int` | Total signal preemption activations performed |
| `corridor_event_log` | `List[Dict[str, Any]]` | Structured lifecycle event audit trail |
| `final_signal_states` | `Dict[str, str]` | Final intersection operating modes at simulation end |
| `recovery_completed` | `bool` | `True` if normal signal operation was fully restored |

---

## 5. `RunComparisonResult` Schema

| Field Name | Type | Formula |
| :--- | :--- | :--- |
| `emergency_response_delta` | `Optional[float]` | `quantumflow.emergency_response_time - baseline.emergency_response_time` |
| `emergency_wait_delta` | `Optional[float]` | `quantumflow.emergency_waiting_time - baseline.emergency_waiting_time` |
| `normal_wait_delta` | `float` | `quantumflow.normal_vehicles_waiting_time - baseline.normal_vehicles_waiting_time` |
| `average_wait_delta` | `float` | `quantumflow.average_waiting_time - baseline.average_waiting_time` |
| `throughput_delta` | `int` | `quantumflow.throughput - baseline.throughput` |
| `max_queue_delta` | `int` | `quantumflow.max_queue - baseline.max_queue` |
| `preemption_delta` | `int` | `quantumflow.emergency_preemption_count - baseline.emergency_preemption_count` |
| `energy_delta` | `float` | `quantumflow.optimization_energy - baseline.optimization_energy` |
