"""Authoritative Complete QUBO Builder and Component Breakdown Evaluator.

Assembles the full multi-intersection traffic optimization QUBO objective:
    H_total = H_onehot + H_wait + H_capacity - H_throughput + H_coupling + H_emergency

Adheres strictly to:
- 12 canonical decision variables defined in optimization.variables.
- Upper-triangular matrix convention: E(x) = x^T Q x.
- Single source of truth: Composes modular functions from onehot.py,
  traffic_objectives.py, coupling.py, and emergency.py without formula duplication.
- Component breakdown diagnostics tracking all 6 objective contributions.
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple, Dict, Any, Union, Optional, List
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.onehot import (
    DEFAULT_ONEHOT_PENALTY,
    add_onehot_penalty,
    evaluate_onehot_penalty,
)
from optimization.traffic_objectives import (
    TrafficObjectiveConfig,
    TrafficState,
    add_wait_term,
    add_capacity_term,
    add_throughput_term,
    evaluate_wait,
    evaluate_capacity,
    evaluate_throughput,
)
from optimization.coupling import (
    CouplingConfig,
    DEFAULT_INTERSECTION_CAPACITY,
    add_coupling_term,
    evaluate_coupling,
    validate_coupling_inputs,
)
from optimization.emergency import (
    DEFAULT_EMERGENCY_WEIGHT,
    DEFAULT_FORCED_DURATION,
    EmergencyConstraints,
    add_emergency_term,
    evaluate_emergency,
)


@dataclass(frozen=True)
class FullQUBOConfig:
    """Master configuration for all multi-intersection QUBO objective hyperparameters.

    Attributes:
        onehot_penalty: Penalty weight A for one-hot constraint (default 100.0).
        wait_weight: Weight B for queue delay penalty (default 2.0).
        capacity_weight: Weight C for capacity overflow penalty (default 10.0).
        capacity_threshold: Critical density threshold (default 0.7).
        throughput_weight: Weight E for vehicle service throughput reward (default 1.0).
        service_rate: Service flow rate mu in veh/sec (default 1.0).
        coupling_weight: Weight D for inter-intersection spillback penalty (default 5.0).
        default_capacity: Default capacity C_j if unspecified in state (default 40.0).
        emergency_weight: Default penalty F for emergency route violations (default 50.0).
    """

    onehot_penalty: float = DEFAULT_ONEHOT_PENALTY  # A = 100.0
    wait_weight: float = 2.0  # B = 2.0
    capacity_weight: float = 10.0  # C = 10.0
    capacity_threshold: float = 0.7
    throughput_weight: float = 1.0  # E = 1.0
    service_rate: float = 1.0  # mu = 1.0
    coupling_weight: float = 5.0  # D = 5.0
    default_capacity: float = DEFAULT_INTERSECTION_CAPACITY  # 40.0
    emergency_weight: float = DEFAULT_EMERGENCY_WEIGHT  # F = 50.0

    def to_traffic_config(self) -> TrafficObjectiveConfig:
        """Extract sub-configuration for local traffic terms."""
        return TrafficObjectiveConfig(
            wait_weight=self.wait_weight,
            capacity_weight=self.capacity_weight,
            capacity_threshold=self.capacity_threshold,
            throughput_weight=self.throughput_weight,
            service_rate=self.service_rate,
        )

    def to_coupling_config(self) -> CouplingConfig:
        """Extract sub-configuration for coupling terms."""
        return CouplingConfig(
            coupling_weight=self.coupling_weight,
            default_capacity=self.default_capacity,
        )


@dataclass(frozen=True)
class ComponentBreakdown:
    """Detailed diagnostic breakdown of all 6 objective term energies for a candidate state x.

    Attributes:
        onehot: Positive penalty incurred from one-hot violations (0.0 if valid).
        wait: Positive queue waiting penalty.
        capacity: Positive capacity threshold penalty.
        throughput_reward: Positive throughput service reward value.
        throughput_cost: Negative QUBO energy contribution (-throughput_reward).
        coupling: Positive inter-intersection spillback penalty.
        emergency: Positive penalty incurred from emergency corridor violations.
        total: Net evaluated objective energy including constant offsets.
    """

    onehot: float
    wait: float
    capacity: float
    throughput_reward: float
    throughput_cost: float
    coupling: float
    emergency: float
    total: float

    def to_dict(self) -> Dict[str, float]:
        """Convert component breakdown to standard dictionary."""
        return {
            "onehot": self.onehot,
            "wait": self.wait,
            "capacity": self.capacity,
            "throughput_reward": self.throughput_reward,
            "throughput_cost": self.throughput_cost,
            "coupling": self.coupling,
            "emergency": self.emergency,
            "total": self.total,
        }


def evaluate_components(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    edges: Sequence[Tuple[str, str]],
    config: FullQUBOConfig = FullQUBOConfig(),
    emergency_constraints: Optional[EmergencyConstraints] = None,
) -> ComponentBreakdown:
    """Direct mathematical evaluation of each individual objective component for candidate state x.

    Mathematical Definition:
        total = onehot + wait + capacity - throughput_reward + coupling + emergency

    Args:
        x: Binary state vector of length 12.
        traffic_state: TrafficState instance or dictionary.
        edges: Directed edge list [(src, dst), ...].
        config: FullQUBOConfig instance.
        emergency_constraints: Active emergency constraints or None.

    Returns:
        ComponentBreakdown: Exact scalar values for each objective component.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    t_cfg = config.to_traffic_config()
    c_cfg = config.to_coupling_config()

    onehot_val = evaluate_onehot_penalty(x, penalty_coefficient=config.onehot_penalty)
    wait_val = evaluate_wait(x, state, t_cfg)
    cap_val = evaluate_capacity(x, state, t_cfg)
    tp_reward = evaluate_throughput(x, state, t_cfg)
    tp_cost = -tp_reward
    coupling_val = evaluate_coupling(x, edges, state, c_cfg)
    emergency_val = evaluate_emergency(x, emergency_constraints)

    total_val = float(
        onehot_val
        + wait_val
        + cap_val
        + tp_cost
        + coupling_val
        + emergency_val
    )

    return ComponentBreakdown(
        onehot=float(onehot_val),
        wait=float(wait_val),
        capacity=float(cap_val),
        throughput_reward=float(tp_reward),
        throughput_cost=float(tp_cost),
        coupling=float(coupling_val),
        emergency=float(emergency_val),
        total=total_val,
    )


def build_qubo(
    traffic_state: Union[TrafficState, Dict[str, Any]],
    edges: Sequence[Tuple[str, str]],
    config: FullQUBOConfig = FullQUBOConfig(),
    emergency_constraints: Optional[EmergencyConstraints] = None,
) -> QUBOModel:
    """Assemble the complete 12-variable upper-triangular QUBO model for multi-intersection optimization.

    Build Sequence:
        1. Initialize Q = 0_{12x12}, offset = 0.0
        2. add_onehot_penalty (Q, offset)
        3. add_wait_term (Q)
        4. add_capacity_term (Q)
        5. add_throughput_term (Q)  [negative reward]
        6. add_coupling_term (Q)
        7. add_emergency_term (Q, offset) [if active]

    Args:
        traffic_state: TrafficState or dictionary.
        edges: Directed edge sequence.
        config: FullQUBOConfig instance.
        emergency_constraints: Active emergency corridor constraints or None.

    Returns:
        QUBOModel: Complete, structured upper-triangular QUBO model.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    t_cfg = config.to_traffic_config()
    c_cfg = config.to_coupling_config()

    # 1. Initialize empty matrix and offset
    Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
    offset = 0.0

    # 2. One-hot quadratic penalty
    Q, offset = add_onehot_penalty(
        Q=Q,
        offset=offset,
        penalty_coefficient=config.onehot_penalty,
    )

    # 3. Local traffic objectives
    add_wait_term(Q, state, t_cfg)
    add_capacity_term(Q, state, t_cfg)
    add_throughput_term(Q, state, t_cfg)

    # 4. Inter-intersection directed coupling
    add_coupling_term(Q, edges, state, c_cfg)

    # 5. Emergency corridor constraints
    if emergency_constraints is not None:
        Q, offset = add_emergency_term(Q, offset, emergency_constraints)

    canonical_var_order = tuple(
        INDEX_TO_VARIABLE[idx] for idx in range(NUM_VARIABLES)
    )

    metadata: Dict[str, Any] = {
        "num_variables": NUM_VARIABLES,
        "intersections": list(INTERSECTIONS),
        "durations": list(DURATIONS),
        "edges": list(edges),
        "config": {
            "onehot_penalty": config.onehot_penalty,
            "wait_weight": config.wait_weight,
            "capacity_weight": config.capacity_weight,
            "capacity_threshold": config.capacity_threshold,
            "throughput_weight": config.throughput_weight,
            "service_rate": config.service_rate,
            "coupling_weight": config.coupling_weight,
            "emergency_weight": config.emergency_weight,
        },
        "has_emergency": emergency_constraints is not None,
        "emergency_route": list(emergency_constraints.route) if emergency_constraints else [],
        "emergency_forced_duration": emergency_constraints.forced_duration if emergency_constraints else None,
        "offset": offset,
    }

    return QUBOModel(
        Q=Q,
        variable_order=canonical_var_order,
        offset=offset,
        metadata=metadata,
    )
