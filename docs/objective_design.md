# QuantumFlow QUBO Objective Formulation & Mathematical Design

## 1. Master QUBO Energy Objective

The master QUBO objective is formulated over 12 canonical binary decision variables $x_{i, t} \in \{0, 1\}$ representing intersection $i \in \{I_1, I_2, I_3, I_4\}$ and green duration $t \in \{15, 30, 45\}\text{ s}$:

$$
H(x) = H_{\text{onehot}}(x) + H_{\text{wait}}(x) + H_{\text{capacity}}(x) - H_{\text{throughput}}(x) + H_{\text{coupling}}(x) + \lambda \cdot H_{\text{emergency}}(x) + H_{\text{starvation}}(x)
$$

with matrix representation in upper-triangular form:
$$
E(x) = x^T Q x + \text{offset}
$$

---

## 2. Component Mathematical Definitions

### 2.1 One-Hot Constraint ($H_{\text{onehot}}$)
Enforces exactly one active green duration per intersection:
$$
H_{\text{onehot}} = A \sum_{i=1}^4 \left( \sum_{t \in \{15, 30, 45\}} x_{i, t} - 1 \right)^2
$$
Expanded:
$$
H_{\text{onehot}} = A \sum_{i=1}^4 \left( -\sum_{t} x_{i, t} + 2 \sum_{t_1 < t_2} x_{i, t_1} x_{i, t_2} \right) + 4A
$$
- Diagonal contribution: $Q[k, k] += -A$
- Off-diagonal pair: $Q[k_1, k_2] += 2A$
- Scalar offset: $\text{offset} += 4A$ (for $A=100.0$, initial offset $= 400.0$)

### 2.2 Local Queue Delay / People-Weighted Waiting ($H_{\text{wait}}$)
Penalizes shorter durations under pending traffic demand:
$$
H_{\text{wait}} = B \sum_{i=1}^4 \sum_{t} \frac{q_i^{\text{eff}}}{t} x_{i, t}
$$
where $q_i^{\text{eff}} = q_i$ in standard vehicle mode, or $q_i^{\text{eff}} = \text{person\_queue}_i = q_i \times \text{occupancy}_i$ in people-aware mode.

### 2.3 Capacity Overflow Penalty ($H_{\text{capacity}}$)
Penalizes allocating less than 45s when local density $d_i$ exceeds capacity threshold (default 0.7):
$$
H_{\text{capacity}} = C \sum_{i=1}^4 \sum_{t} \max(0, d_i - d_{\text{thresh}}) (45 - t) x_{i, t}
$$

### 2.4 Throughput Service Reward ($-H_{\text{throughput}}$)
Rewards vehicle departures proportional to allocated green time up to queue saturation $\mu \cdot t$:
$$
H_{\text{throughput}} = E \sum_{i=1}^4 \sum_{t} \min(q_i, \mu \cdot t) x_{i, t}
$$

### 2.5 Arterial Network Coupling ($H_{\text{coupling}}$)
Harmonizes downstream signal progression along directed arterial edges $(i, j)$:
$$
H_{\text{coupling}} = D \sum_{(i, j) \in \mathcal{E}} \sum_{t_i, t_j} \frac{|t_i - t_j|}{45} x_{i, t_i} x_{j, t_j}
$$

### 2.6 Dynamic Emergency Corridor ($H_{\text{emergency}}$)
Enforces maximum green allocation ($45\text{s}$) along an active emergency route:
$$
H_{\text{emergency}} = F \sum_{k \in \text{route}} (1 - x_{k, 45}) = F |\text{route}| - F \sum_{k \in \text{route}} x_{k, 45}
$$
Parameterized by $\lambda \in [0.0, 1.0]$ in multi-objective trade-off sweeps.

### 2.7 Starvation and Fairness Penalty ($H_{\text{starvation}}$)
Penalizes under-allocating green time to approaches whose accumulated delay exceeds a starvation threshold $W_{\text{cap}}$:
$$
H_{\text{starvation}} = G \sum_{i=1}^4 \sum_{t} \frac{\max(0, W_i - W_{\text{cap}})}{W_{\text{cap}}} (45 - t) x_{i, t}
$$
