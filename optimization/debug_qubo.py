"""Developer CLI Diagnostic Tool for Complete QUBO Inspection and Exhaustive Enumeration.

Usage:
    python -m optimization.debug_qubo
"""

import sys
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    VARIABLE_NAMES,
)
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import (
    FullQUBOConfig,
    build_qubo,
    evaluate_components,
)
from optimization.enumeration import enumerate_qubo_states
from optimization.decoder import decode_solution


def run_diagnostics() -> None:
    """Execute complete deterministic diagnostic benchmark and print formatted reports."""
    print("=" * 80)
    print("QUANTUMFLOW QUBO DIAGNOSTIC & EXHAUSTIVE ENUMERATION ENGINE")
    print("=" * 80)

    # 1. Deterministic Traffic Scenario
    state_dict = {
        "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
        "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
        "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
        "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
    }
    traffic_state = TrafficState.from_dict(state_dict)
    edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]

    # Emergency Corridor on I2 -> I3 -> I4
    emergency_constraints = EmergencyConstraints(
        route=["I2", "I3", "I4"],
        forced_duration=45,
        emergency_weight=50.0,
    )

    config = FullQUBOConfig(
        onehot_penalty=100.0,  # A
        wait_weight=2.0,       # B
        capacity_weight=10.0,  # C
        capacity_threshold=0.7,
        throughput_weight=1.0, # E
        service_rate=1.0,      # mu
        coupling_weight=5.0,   # D
        default_capacity=100.0,
        emergency_weight=50.0, # F
    )

    print("\n1. CANONICAL VARIABLE ORDERING (12 Binary Variables):")
    print("-" * 50)
    for idx in range(NUM_VARIABLES):
        inter, dur = INDEX_TO_VARIABLE[idx]
        name = VARIABLE_NAMES[idx]
        print(f"  Index {idx:2d} -> {name:7s} (Intersection: {inter}, Duration: {dur}s)")

    # 2. Build Complete QUBO Model
    model = build_qubo(
        traffic_state=traffic_state,
        edges=edges,
        config=config,
        emergency_constraints=emergency_constraints,
    )

    print("\n2. QUBO MODEL PARAMETERS & OFFSET:")
    print("-" * 50)
    print(f"  Matrix Shape: {model.Q.shape} (Upper-Triangular)")
    print(f"  Constant Energy Offset: {model.offset:.4f}")
    print(f"    - One-Hot Offset (4 * 100.0): 400.0")
    print(f"    - Emergency Offset (3 * 50.0): 150.0")
    print(f"    - Total Expected Offset: 550.0")

    # 3. Non-Zero Matrix Entries
    print("\n3. NON-ZERO UPPER-TRIANGULAR Q MATRIX INTERACTIONS:")
    print("-" * 50)
    rows, cols = np.nonzero(model.Q)
    for r, c in zip(rows, cols):
        val = model.Q[r, c]
        if not np.isclose(val, 0.0):
            var_r = VARIABLE_NAMES[r]
            var_c = VARIABLE_NAMES[c]
            if r == c:
                print(f"  Q[{r:2d}, {c:2d}] (Diagonal {var_r:7s})     = {val:+10.4f}")
            else:
                print(f"  Q[{r:2d}, {c:2d}] (Pairwise {var_r} * {var_c}) = {val:+10.4f}")

    # 4. Exhaustive State Space Enumeration (2^12 = 4096 states)
    print("\n4. EXHAUSTIVE STATE SPACE ENUMERATION (4096 States):")
    print("-" * 50)
    analysis = enumerate_qubo_states(
        qubo_model=model,
        traffic_state=traffic_state,
        edges=edges,
        config=config,
        emergency_constraints=emergency_constraints,
    )

    print(f"  Total States Evaluated:    {analysis.total_states_count:4d}")
    print(f"  One-Hot Valid States:      {analysis.onehot_valid_count:4d} (Expected 3^4 = 81)")
    print(f"  Emergency-Compliant Valid: {analysis.emergency_valid_count:4d} (Expected 3^(4-3) = 3)")
    print(f"  Is Unconstrained Min Valid: {analysis.is_unconstrained_valid}")

    # 5. Best Unconstrained State
    bu = analysis.best_unconstrained
    print("\n5. GLOBAL UNCONSTRAINED OPTIMUM (Across all 4096 states):")
    print("-" * 50)
    print(f"  Bitstring:      {bu.bitstring}")
    print(f"  Total Energy:   {bu.energy:.4f}")
    print(f"  One-Hot Valid:  {bu.is_valid_onehot}")
    print(f"  Emergency Valid:{bu.is_valid_emergency}")
    print(f"  Components:")
    for k, v in bu.components.to_dict().items():
        print(f"    - {k:18s}: {v:+10.4f}")

    # 6. Best One-Hot Valid State
    bv = analysis.best_onehot_valid
    print("\n6. BEST ONE-HOT VALID STATE (Across 81 valid signal plans):")
    print("-" * 50)
    if bv:
        print(f"  Bitstring:      {bv.bitstring}")
        print(f"  Total Energy:   {bv.energy:.4f}")
        print(f"  Signal Plan:    {bv.signal_plan}")
        print(f"  Emergency Valid:{bv.is_valid_emergency}")
        print(f"  Components:")
        for k, v in bv.components.to_dict().items():
            print(f"    - {k:18s}: {v:+10.4f}")

    # 7. Best Emergency Valid State
    be = analysis.best_emergency_valid
    print("\n7. BEST EMERGENCY CORRIDOR COMPLIANT STATE (Across 3 emergency plans):")
    print("-" * 50)
    if be:
        print(f"  Bitstring:      {be.bitstring}")
        print(f"  Total Energy:   {be.energy:.4f}")
        print(f"  Signal Plan:    {be.signal_plan}")
        print(f"  Components:")
        for k, v in be.components.to_dict().items():
            print(f"    - {k:18s}: {v:+10.4f}")

    print("\n" + "=" * 80)
    print("QUBO DIAGNOSTICS COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnostics()
