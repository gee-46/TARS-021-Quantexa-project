# Multi-Emergency Conflict Resolution & Preemption Architecture

## 1. Multi-Emergency Operational Challenge

In dense urban networks, multiple emergency vehicles (ambulances, fire engines, police units) may enter the network concurrently with intersecting routes.

### Example Contention Scenario:
- **Emergency A**: Traverses corridor $I_1 \to I_2 \to I_3$ (Eastbound).
- **Emergency B**: Traverses corridor $I_4 \to I_3 \to I_2$ (Westbound).

Both vehicles require preemption at node $I_3$ at overlapping arrival windows. Granting simultaneous green to opposing movements violates signal safety.

---

## 2. Hierarchical Two-Stage Optimization

QuantumFlow separates normal traffic optimization from emergency conflict resolution:

```
Normal Traffic QUBO (12 Qubits)
        ↓
Normal Green Plan (e.g. I1=30, I2=45, I3=15, I4=30)
        ↓
Emergency Arrival & Conflict Detection
        ↓
Conflict Graph & Arrival Window Estimation
        ↓
Emergency Sequencing QUBO (K vehicles x K time slots)
        ↓
QAOA / SA Fallback Solver
        ↓
Conflict-Free Clearance Schedule (Non-overlapping Intervals)
        ↓
Microscopic Dynamic Preemption Override
        ↓
Corridor Clearance & Safe Resumption of Normal Signal Plan
```

---

## 3. Conflict QUBO Formulation

For $K$ contending emergency vehicles at intersection $J$, let binary decision variable $y_{v, s} \in \{0, 1\}$ indicate whether vehicle $v \in \{1, \dots, K\}$ is allocated sequence slot $s \in \{1, \dots, K\}$:

$$
H_{\text{conflict}}(y) = P_1 \sum_{v=1}^K \left(\sum_{s=1}^K y_{v, s} - 1\right)^2 + P_2 \sum_{s=1}^K \left(\sum_{v=1}^K y_{v, s} - 1\right)^2 + \sum_{v=1}^K \sum_{s=1}^K w_{v, s} \cdot y_{v, s}
$$

where the priority cost is:
$$
w_{v, s} = \alpha \cdot \text{estimated\_arrival}_v \cdot s + \beta \cdot (4 - \text{priority}_v) \cdot s
$$

### Clearance Scheduling:
Given the optimal sequence $(v_{(1)}, v_{(2)}, \dots, v_{(K)})$, non-overlapping clearance intervals $[t_{\text{start}}^{(k)}, t_{\text{end}}^{(k)}]$ are calculated dynamically:
$$
t_{\text{start}}^{(k)} = \max\left(\text{ETA}_{v_{(k)}}, t_{\text{end}}^{(k-1)}\right)
$$
$$
t_{\text{end}}^{(k)} = t_{\text{start}}^{(k)} + \Delta_{\text{clearance}}
$$

---

## 4. Progressive Corridor Preemption Controller

The `EmergencyCorridorController` tracks multi-vehicle states:
1. **Lookahead Detection**: Flags upcoming intersections $T_{\text{lookahead}}$ seconds prior to vehicle arrival.
2. **Dynamic Green Force**: Forces green phase for current and immediate downstream nodes.
3. **Progressive Clearance**: As vehicle clears intersection $i$, normal signal operation is immediately restored at node $i$ while downstream nodes maintain green.
4. **Resumption**: When all emergency vehicles complete their journeys, normal adaptive signal plans resume seamlessly.
