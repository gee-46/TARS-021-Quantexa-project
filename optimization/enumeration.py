"""Exact Exhaustive Enumeration and Solution Analysis for 12-Variable QUBO.

Performs deterministic brute-force evaluation over all 2^12 = 4096 binary state vectors to find:
1. Global Unconstrained Minimum: argmin_{x in {0,1}^12} E(x)
2. Best One-Hot-Valid Minimum: argmin_{x in ValidOneHot} E(x)  [81 valid signal plans]
3. Best Emergency-Valid Minimum: argmin_{x in ValidEmergency} E(x) [3^(4-m) plans]

Provides ground-truth baseline for benchmarking QAOA and Classical Simulated Annealing.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple, Dict, Any, List, Optional, Union
import itertools
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import (
    FullQUBOConfig,
    ComponentBreakdown,
    evaluate_components,
    build_qubo,
)
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
)


@dataclass(frozen=True)
class StateRecord:
    """Detailed record for a single evaluated binary state vector.

    Attributes:
        bitstring: 12-character binary string, e.g. "010001100001".
        state: 12-tuple of binary integer bits (0 or 1).
        energy: Total evaluated objective energy (x^T Q x + offset).
        is_valid_onehot: True if exactly one duration selected per intersection.
        is_valid_emergency: True if active emergency route requirements are satisfied.
        signal_plan: Decoded dictionary {"I1": 30, ...} if one-hot valid, else None.
        components: ComponentBreakdown of individual objective contributions.
    """

    bitstring: str
    state: Tuple[int, ...]
    energy: float
    is_valid_onehot: bool
    is_valid_emergency: bool
    signal_plan: Optional[Dict[str, int]]
    components: ComponentBreakdown


@dataclass(frozen=True)
class ExhaustiveAnalysisResult:
    """Comprehensive analytical summary of exhaustive state space enumeration.

    Attributes:
        total_states_count: Exactly 4096 for 12 binary variables.
        onehot_valid_count: Exactly 81 (3^4) valid signal timing configurations.
        emergency_valid_count: Exact count of emergency-compliant one-hot configurations.
        best_unconstrained: Lowest energy state across all 4096 states.
        best_onehot_valid: Lowest energy state among one-hot valid configurations.
        best_emergency_valid: Lowest energy state among emergency-compliant valid configurations.
        is_unconstrained_valid: True if global unconstrained minimum is one-hot valid.
        all_records: List of all 4096 evaluated StateRecord instances sorted by energy.
    """

    total_states_count: int
    onehot_valid_count: int
    emergency_valid_count: int
    best_unconstrained: StateRecord
    best_onehot_valid: Optional[StateRecord]
    best_emergency_valid: Optional[StateRecord]
    is_unconstrained_valid: bool
    all_records: List[StateRecord]


def enumerate_qubo_states(
    qubo_model: QUBOModel,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    edges: Sequence[Tuple[str, str]],
    config: FullQUBOConfig = FullQUBOConfig(),
    emergency_constraints: Optional[EmergencyConstraints] = None,
) -> ExhaustiveAnalysisResult:
    """Enumerate all 4096 binary states and perform exhaustive global optimization analysis.

    Args:
        qubo_model: Compiled QUBOModel (12x12 upper-triangular Q and offset).
        traffic_state: TrafficState instance or dict.
        edges: Directed edge sequence.
        config: FullQUBOConfig instance.
        emergency_constraints: Active EmergencyConstraints or None.

    Returns:
        ExhaustiveAnalysisResult: Complete ground-truth optimization analysis.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    records: List[StateRecord] = []

    # Enumerate all 2^12 = 4096 combinations
    for bits in itertools.product([0, 1], repeat=NUM_VARIABLES):
        x_tuple = tuple(bits)
        bitstr = "".join(str(b) for b in bits)

        # 1. Evaluate total energy via QUBOModel
        energy_val = qubo_model.energy(x_tuple, include_offset=True)

        # 2. Check validity
        valid_onehot = is_valid_onehot(x_tuple)
        valid_emergency = is_valid_emergency(x_tuple, emergency_constraints)

        # 3. Decode signal plan if valid
        signal_plan = decode_solution(x_tuple) if valid_onehot else None

        # 4. Component breakdown
        comp = evaluate_components(
            x=x_tuple,
            traffic_state=state,
            edges=edges,
            config=config,
            emergency_constraints=emergency_constraints,
        )

        record = StateRecord(
            bitstring=bitstr,
            state=x_tuple,
            energy=float(energy_val),
            is_valid_onehot=valid_onehot,
            is_valid_emergency=valid_emergency,
            signal_plan=signal_plan,
            components=comp,
        )
        records.append(record)

    # Sort all states by energy (lowest energy first)
    records.sort(key=lambda r: r.energy)

    # Best unconstrained state
    best_unconstrained = records[0]

    # Best one-hot valid state
    onehot_valid_records = [r for r in records if r.is_valid_onehot]
    best_onehot_valid = onehot_valid_records[0] if onehot_valid_records else None

    # Best emergency valid state (must be both one-hot valid and emergency compliant)
    emergency_valid_records = [
        r for r in records if r.is_valid_onehot and r.is_valid_emergency
    ]
    best_emergency_valid = emergency_valid_records[0] if emergency_valid_records else None

    is_unconstrained_valid = best_unconstrained.is_valid_onehot and (
        emergency_constraints is None or best_unconstrained.is_valid_emergency
    )

    return ExhaustiveAnalysisResult(
        total_states_count=len(records),
        onehot_valid_count=len(onehot_valid_records),
        emergency_valid_count=len(emergency_valid_records),
        best_unconstrained=best_unconstrained,
        best_onehot_valid=best_onehot_valid,
        best_emergency_valid=best_emergency_valid,
        is_unconstrained_valid=is_unconstrained_valid,
        all_records=records,
    )
