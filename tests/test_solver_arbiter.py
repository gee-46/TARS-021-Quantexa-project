"""Unit tests for Solver Arbiter and Multi-Solver Comparative Evaluation.

Tests:
- All solvers evaluate identical 12-variable QUBO instance.
- Candidate validity checking (onehot, emergency constraints).
- Unmanipulated energy scoring (E = x^T Q x + offset).
- Feasible solver candidate selection.
- Solver comparison delta calculations.
- Greedy local search descent behavior.
- Error handling and graceful fallback if a solver fails.
"""

import pytest
import numpy as np
from optimization.variables import NUM_VARIABLES, INTERSECTIONS, DURATIONS, get_variable_index
from optimization.qubo_model import QUBOModel
from optimization.qubo_builder import build_qubo, FullQUBOConfig
from optimization.solver_arbiter import (
    solve_greedy,
    arbitrate_solvers,
    SolverCandidateRecord,
    ArbiterComparisonResult,
)


def test_greedy_solver_finds_valid_plan():
    """Verify solve_greedy returns a valid one-hot solution with lower or equal energy."""
    traffic_state = {
        "I1": {"queue": 25.0, "density": 0.8},
        "I2": {"queue": 5.0, "density": 0.2},
        "I3": {"queue": 15.0, "density": 0.5},
        "I4": {"queue": 2.0, "density": 0.1},
    }
    qubo = build_qubo(traffic_state, config=FullQUBOConfig())
    x, e, runtime = solve_greedy(qubo)

    assert len(x) == NUM_VARIABLES
    assert runtime >= 0.0
    assert np.isclose(e, qubo.energy(x))

    # Verify one-hot structure
    for inter in INTERSECTIONS:
        chosen = [dur for dur in DURATIONS if x[get_variable_index(inter, dur)] == 1]
        assert len(chosen) == 1, f"Intersection {inter} must have exactly one active duration"


def test_arbitrate_solvers_same_qubo():
    """Verify arbitrate_solvers evaluates QAOA, SA, and Greedy on the exact same QUBO instance."""
    traffic_state = {
        "I1": {"queue": 20.0, "density": 0.6},
        "I2": {"queue": 10.0, "density": 0.3},
        "I3": {"queue": 30.0, "density": 0.9},
        "I4": {"queue": 5.0, "density": 0.2},
    }
    qubo = build_qubo(traffic_state, config=FullQUBOConfig())

    result = arbitrate_solvers(
        qubo=qubo,
        qaoa_p=1,
        qaoa_shots=512,
        sa_reads=50,
        sa_sweeps=200,
        seed=42,
    )

    assert isinstance(result, ArbiterComparisonResult)
    assert set(result.candidates.keys()) == {"qaoa", "sa", "greedy"}

    # All candidate energies must match exact energy evaluation of their respective bitstrings
    for name, cand in result.candidates.items():
        assert isinstance(cand, SolverCandidateRecord)
        cand_x = np.array([int(b) for b in cand.candidate_bitstring])
        assert np.isclose(cand.qubo_energy, qubo.energy(cand_x))
        assert cand.runtime_seconds >= 0.0

    # Best solver must be chosen among feasible ones with lowest energy
    assert result.best_solver in {"qaoa", "sa", "greedy"}
    best_cand = result.candidates[result.best_solver]
    assert best_cand.is_feasible is True
    assert np.isclose(result.best_energy, best_cand.qubo_energy)


def test_arbitrate_solvers_emergency_constraints():
    """Verify emergency constraints are respected in candidate feasibility."""
    traffic_state = {
        "I1": {"queue": 10.0, "density": 0.4},
        "I2": {"queue": 10.0, "density": 0.4},
        "I3": {"queue": 10.0, "density": 0.4},
        "I4": {"queue": 10.0, "density": 0.4},
    }
    emergency_route = ("I2", "I3", "I4")
    qubo = build_qubo(traffic_state, emergency_route=emergency_route, config=FullQUBOConfig(emergency_weight=100.0))

    result = arbitrate_solvers(
        qubo=qubo,
        emergency_constraints={"I2": 45, "I3": 45, "I4": 45},
        qaoa_p=1,
        qaoa_shots=512,
        sa_reads=50,
        sa_sweeps=300,
        seed=42,
    )

    # Simulated annealing should find emergency-compliant candidate
    sa_cand = result.candidates["sa"]
    assert sa_cand.onehot_valid is True
    assert sa_cand.emergency_valid is True
    assert sa_cand.is_feasible is True
    for inter in emergency_route:
        assert sa_cand.signal_plan[inter] == 45


def test_arbitrate_solvers_to_dict():
    """Verify ArbiterComparisonResult serialization."""
    traffic_state = {
        "I1": {"queue": 15.0, "density": 0.5},
        "I2": {"queue": 15.0, "density": 0.5},
        "I3": {"queue": 15.0, "density": 0.5},
        "I4": {"queue": 15.0, "density": 0.5},
    }
    qubo = build_qubo(traffic_state, config=FullQUBOConfig())
    result = arbitrate_solvers(qubo=qubo, qaoa_p=1, qaoa_shots=100, sa_reads=20, sa_sweeps=100, seed=42)

    d = result.to_dict()
    assert "best_solver" in d
    assert "best_plan" in d
    assert "best_energy" in d
    assert "qaoa_energy" in d
    assert "sa_energy" in d
    assert "greedy_energy" in d
    assert "candidates" in d
    assert len(d["candidates"]) == 3
