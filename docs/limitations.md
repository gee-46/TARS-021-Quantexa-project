# QuantumFlow System Assumptions, Limitations, & Honest Disclaimers

## 1. Quantum Computing Limitations & NISQ Context

1. **Simulated Hardware**: QAOA is executed using classical gate-level simulation on Qiskit Aer (`AerSimulator`), unless configured with external cloud access to physical QPUs.
2. **No Claim of Quantum Advantage**: For 12-variable binary optimization problems, exact exhaustive enumeration ($2^{12} = 4096$ states) and classical metaheuristics (Simulated Annealing, ILP) execute in milliseconds and find the exact optimum reliably. QAOA at $p=1$ serves as an algorithmic demonstration and NISQ proof-of-concept, not an operational speedup claim.
3. **Parameter Optimization Overhead**: Classical outer-loop parameter optimization (e.g. COBYLA) requires multiple circuit shot evaluations per iteration, resulting in higher execution latency relative to pure classical heuristics.

---

## 2. Traffic Modeling Assumptions

1. **Discrete-Time Network**: The microscopic simulator operates at discrete 1-second intervals along a 4-intersection arterial grid ($I_1 \to I_2 \to I_3 \to I_4$).
2. **Deterministic Vehicle Flow**: Arrival processes are governed by pseudo-random Poisson distributions conditioned on reproducible seeds.
3. **Simplified Turning Movements**: Arterial corridor flow is prioritized with simplified opposing turn movement modeling.
4. **Emissions Model**: Fuel burn ($0.7\text{ L/veh-hr}$) and $\text{CO}_2$ ($2.31\text{ kg/L}$) represent empirical EPA idling estimates based on stationary queuing delay rather than dynamic instantaneous acceleration/deceleration engine load telemetry.

---

## 3. Operational Invariants

1. **Cycle Boundary Synchronization**: To prevent chaotic signal phase jumps, adaptive rolling-horizon plan updates are strictly enforced only at periodic 60-second cycle boundaries.
2. **Emergency Separation**: Real-time emergency vehicle arrivals do not interrupt or re-trigger QAOA optimization; they invoke high-speed deterministic green corridor preemption, seamlessly restoring the active adaptive plan once the emergency clears.

---

## 4. Release Scope Statements (Simulator-Based Demo)

1. **Whole-junction preemption**: emergency preemption forces the entire junction green; turn phases and per-approach signal groups are not modelled.
2. **Assumed traffic**: all traffic volumes, occupancies and cross-street demands are simulated/assumed unless explicitly backed by measured data; none are.
3. **Pareto assumptions**: Pareto results depend on the configured cross-street traffic assumption (`cross_street_rate`) and on the preemption-duty interpretation of lambda.
4. **Classical simulation of QAOA**: QAOA is executed on Qiskit Aer. Ideal-vs-noisy simulation uses a generic noise model, not a calibrated device.
5. **Real hardware unverified**: the IBM runtime path is implemented but has not been executed on a real account/device; no hardware results, timings or fidelities are reported anywhere.
6. **Belagavi**: the Belagavi content is a Belagavi-inspired schematic / illustrative topology, not a digital twin.
7. **No quantum advantage is claimed.**
