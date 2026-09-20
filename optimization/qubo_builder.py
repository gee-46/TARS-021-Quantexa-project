"""Authoritative Complete QUBO Builder and Component Breakdown Evaluator.

Assembles the full multi-intersection traffic optimization QUBO objective:
    H_total = H_onehot + H_wait + H_capacity - H_throughput + H_coupling + H_emergency + H_starvation

Adheres strictly to:
- 12 canonical decision variables defined in optimization.variables.
- Upper-triangular matrix convention: E(x) = x^T Q x.
- Single source of truth: Composes modular functions from onehot.py,
  traffic_objectives.py, coupling.py, and emergency.py without formula duplication.
- Component breakdown diagnostics tracking all objective contributions.
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
    add_starvation_fairness_term,
    add_traffic_terms,
    evaluate_wait,
    evaluate_capacity,
    evaluate_throughput,
    evaluate_starvation_fairness,
    evaluate_local_traffic_qubo_energy,
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


# Cross-street delay weight used when a scenario models cross traffic (off otherwise). Calibrated by simulation sweep over five
# cross-traffic cases (Belagavi-inspired normal / peak / peak+2 ambulances, scenario D with 0.3 and 0.5 veh/s cross demand):
# w = 0.5 had the lowest worst-case regret (4.2%, mean 1.6%) in total civilian person-delay versus the best of {fixed 30 s,
# all 45 s, QUBO at any swept weight}. w = 0 (cross street ignored) had 85% worst-case regret. In-sample calibration; see docs.
CROSS_STREET_WEIGHT = 0.5


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
        person_weighted: If True, weights H_wait by passenger counts.
        fairness_weight: Weight for delay equity across intersections.
        starvation_penalty_weight: Weight for penalizing approaches exceeding max_wait_cap.
        max_wait_cap: Maximum acceptable delay in seconds before starvation penalty.
        lambda_tradeoff: Trade-off parameter (1.0 = full emergency priority, 0.0 = civilian only).
        cross_street_weight: Cross-street delay weight (0.0 = off, the default; see add_cross_street_term).
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
    person_weighted: bool = False
    fairness_weight: float = 0.0
    starvation_penalty_weight: float = 0.0
    max_wait_cap: float = 120.0
    lambda_tradeoff: float = 1.0
    cross_street_weight: float = 0.0

    def to_traffic_config(self) -> TrafficObjectiveConfig:
        """Extract sub-configuration for local traffic terms."""
        return TrafficObjectiveConfig(
            wait_weight=self.wait_weight,
            capacity_weight=self.capacity_weight,
            capacity_threshold=self.capacity_threshold,
            throughput_weight=self.throughput_weight,
            service_rate=self.service_rate,
            person_weighted=self.person_weighted,
            fairness_weight=self.fairness_weight,
            starvation_penalty_weight=self.starvation_penalty_weight,
            max_wait_cap=self.max_wait_cap,
            cross_street_weight=self.cross_street_weight,
        )

    def to_coupling_config(self) -> CouplingConfig:
        """Extract sub-configuration for coupling terms."""
        return CouplingConfig(
            coupling_weight=self.coupling_weight,
            default_capacity=self.default_capacity,
        )


@dataclass(frozen=True)
class ComponentBreakdown:
    """Detailed diagnostic breakdown of all objective term energies for a candidate state x.

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
    total_energy: float = 0.0
    onehot_energy: float = 0.0
    wait_energy: float = 0.0
    capacity_energy: float = 0.0
    throughput_energy: float = 0.0
    coupling_energy: float = 0.0
    emergency_energy: float = 0.0
    is_feasible_onehot: bool = True
    is_feasible_emergency: bool = True

    def to_dict(self) -> Dict[str, Any]:
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
            "total_energy": self.total_energy if self.total_energy != 0.0 else self.total,
            "onehot_energy": self.onehot_energy,
            "wait_energy": self.wait_energy,
            "capacity_energy": self.capacity_energy,
            "throughput_energy": self.throughput_energy,
            "coupling_energy": self.coupling_energy,
            "emergency_energy": self.emergency_energy,
            "is_feasible_onehot": self.is_feasible_onehot,
            "is_feasible_emergency": self.is_feasible_emergency,
        }


# Backward-compatible alias
QUBOComponentBreakdown = ComponentBreakdown


def _resolve_build_qubo_args(
    traffic_state: Union[TrafficState, Dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> Tuple[TrafficState, List[Tuple[str, str]], FullQUBOConfig, Optional[EmergencyConstraints]]:
    """Flexibly resolve positional and keyword arguments across diverse call conventions."""
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    resolved_edges: List[Tuple[str, str]] = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
    resolved_config: FullQUBOConfig = FullQUBOConfig()
    resolved_emergency: Optional[EmergencyConstraints] = None

    for item in args:
        if item is None:
            continue
        elif isinstance(item, FullQUBOConfig):
            resolved_config = item
        elif isinstance(item, EmergencyConstraints):
            resolved_emergency = item
        elif isinstance(item, (list, tuple)):
            if len(item) > 0 and isinstance(item[0], (list, tuple)) and len(item[0]) == 2 and isinstance(item[0][0], str):
                resolved_edges = [tuple(e) for e in item]  # type: ignore
            elif len(item) > 0 and isinstance(item[0], str):
                resolved_emergency = EmergencyConstraints(route=item)
            elif len(item) == 0:
                resolved_edges = []
        elif isinstance(item, dict):
            if "route" in item:
                resolved_emergency = EmergencyConstraints(**item)

    if "edges" in kwargs and kwargs["edges"] is not None:
        resolved_edges = [tuple(e) for e in kwargs["edges"]]  # type: ignore
    if "config" in kwargs and kwargs["config"] is not None:
        resolved_config = kwargs["config"]
    if "emergency_constraints" in kwargs and kwargs["emergency_constraints"] is not None:
        em = kwargs["emergency_constraints"]
        if isinstance(em, EmergencyConstraints):
            resolved_emergency = em
        elif isinstance(em, (list, tuple)):
            resolved_emergency = EmergencyConstraints(route=em)
        elif isinstance(em, dict):
            resolved_emergency = EmergencyConstraints(**em)

    return state, resolved_edges, resolved_config, resolved_emergency


def build_qubo(
    traffic_state: Union[TrafficState, Dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> QUBOModel:
    """Build the authoritative 12-variable multi-intersection traffic QUBO model.

    Assembles:
        Q = Q_onehot + Q_wait + Q_capacity - Q_throughput + Q_coupling + (lambda * Q_emergency) + Q_starvation
    """
    state, resolved_edges, config, resolved_emergency = _resolve_build_qubo_args(traffic_state, *args, **kwargs)
    Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=float)
    offset = 0.0

    # 1. One-Hot Constraint Term (A)
    Q, offset = add_onehot_penalty(Q, offset, penalty_coefficient=config.onehot_penalty)

    # 2. Local Traffic Terms (B, C, E, Fairness, Starvation)
    t_cfg = config.to_traffic_config()
    add_traffic_terms(Q, state, t_cfg)

    # 3. Inter-Intersection Coupling Terms (D)
    c_cfg = config.to_coupling_config()
    if resolved_edges:
        add_coupling_term(Q, resolved_edges, state, c_cfg)

    # 4. Emergency Route Prioritization Term (F * lambda)
    if resolved_emergency is not None and config.lambda_tradeoff > 0.0:
        if config.lambda_tradeoff != 1.0:
            eff_weight = resolved_emergency.emergency_weight * config.lambda_tradeoff
            eff_em = EmergencyConstraints(
                route=resolved_emergency.route,
                forced_duration=resolved_emergency.forced_duration,
                emergency_weight=eff_weight,
            )
        else:
            eff_em = resolved_emergency
        Q, offset = add_emergency_term(Q, offset, eff_em)

    canonical_var_order = tuple(
        INDEX_TO_VARIABLE[idx] for idx in range(NUM_VARIABLES)
    )

    metadata: Dict[str, Any] = {
        "num_variables": NUM_VARIABLES,
        "intersections": list(INTERSECTIONS),
        "durations": list(DURATIONS),
        "edges": list(resolved_edges),
        "config": {
            "onehot_penalty": config.onehot_penalty,
            "wait_weight": config.wait_weight,
            "capacity_weight": config.capacity_weight,
            "throughput_weight": config.throughput_weight,
            "coupling_weight": config.coupling_weight,
            "emergency_weight": config.emergency_weight,
            "person_weighted": config.person_weighted,
            "fairness_weight": config.fairness_weight,
            "starvation_penalty_weight": config.starvation_penalty_weight,
            "lambda_tradeoff": config.lambda_tradeoff,
        },
        "has_emergency": resolved_emergency is not None,
        "emergency_route": list(resolved_emergency.route) if resolved_emergency else [],
        "emergency_forced_duration": resolved_emergency.forced_duration if resolved_emergency else None,
        "offset": offset,
    }

    return QUBOModel(
        Q=Q,
        variable_order=canonical_var_order,
        offset=offset,
        metadata=metadata,
    )


def evaluate_components(
    x: Union[np.ndarray, Sequence[int], str],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> ComponentBreakdown:
    """Direct mathematical evaluation of each individual objective component for candidate state x."""
    state, resolved_edges, config, resolved_emergency = _resolve_build_qubo_args(traffic_state, *args, **kwargs)
    t_cfg = config.to_traffic_config()
    c_cfg = config.to_coupling_config()

    if isinstance(x, str):
        x_vec = tuple(int(c) for c in x)
    else:
        x_vec = tuple(int(b) for b in x)

    onehot_val = evaluate_onehot_penalty(x_vec, penalty_coefficient=config.onehot_penalty)
    wait_val = evaluate_wait(x_vec, state, t_cfg)
    cap_val = evaluate_capacity(x_vec, state, t_cfg)
    tp_reward = evaluate_throughput(x_vec, state, t_cfg)
    tp_cost = -tp_reward
    coupling_val = evaluate_coupling(x_vec, resolved_edges, state, c_cfg) if resolved_edges else 0.0
    emergency_val = evaluate_emergency(x_vec, resolved_emergency) if resolved_emergency else 0.0

    total_val = float(
        onehot_val
        + wait_val
        + cap_val
        + tp_cost
        + coupling_val
        + emergency_val
    )

    from optimization.decoder import is_valid_onehot, is_valid_emergency
    feasible_oh = is_valid_onehot(x_vec)
    feasible_em = is_valid_emergency(x_vec, resolved_emergency) if resolved_emergency else True

    return ComponentBreakdown(
        onehot=float(onehot_val),
        wait=float(wait_val),
        capacity=float(cap_val),
        throughput_reward=float(tp_reward),
        throughput_cost=float(tp_cost),
        coupling=float(coupling_val),
        emergency=float(emergency_val),
        total=total_val,
        total_energy=total_val,
        onehot_energy=float(onehot_val),
        wait_energy=float(wait_val),
        capacity_energy=float(cap_val),
        throughput_energy=float(tp_cost),
        coupling_energy=float(coupling_val),
        emergency_energy=float(emergency_val),
        is_feasible_onehot=feasible_oh,
        is_feasible_emergency=feasible_em,
    )
