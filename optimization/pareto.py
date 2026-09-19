"""Pareto Multi-Objective Trade-Off Analysis for QuantumFlow.

Evaluates the trade-off frontier between Emergency Vehicle Prioritization (lambda)
and Civilian / Transit Person-Delay Impact across a sweep of lambda in [0.0, 1.0].

In the master QUBO:
    H(lambda) = H_civilian + (lambda * H_emergency)
where lambda = 0.0 optimizes purely for civilian traffic throughput and delay,
and lambda = 1.0 enforces full dynamic emergency corridor wave holds.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Sequence
import numpy as np

from simulation.scenario import SimulationScenario, EmergencyVehicleConfig
from simulation.engine import TrafficSimulator
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.hybrid_solver import solve_hybrid
from simulation.emissions import calculate_emissions


@dataclass(frozen=True)
class ParetoPoint:
    """A single evaluated operational operating point on the Pareto trade-off frontier.

    Attributes:
        lambda_param: Trade-off weight lambda in [0.0, 1.0].
        emergency_response_time: Emergency vehicle travel seconds (or None).
        emergency_waiting_time: Emergency vehicle queuing delay seconds.
        civilian_waiting_time: Cumulative normal vehicle waiting seconds.
        person_delay: Total civilian person-seconds of waiting delay.
        throughput: Total vehicles completing their routes.
        jain_fairness_index: Fairness index across all approach wait distributions.
        estimated_co2_kg: Carbon emissions produced during simulation.
        qubo_energy: Solved QUBO objective value.
        signal_plan: Decoded signal timing allocation {"I1": 30, ...}.
        solver_used: Solver that produced the plan ("qaoa" or "sa").
    """

    lambda_param: float
    emergency_response_time: Optional[float]
    emergency_waiting_time: Optional[float]
    civilian_waiting_time: float
    person_delay: float
    throughput: int
    jain_fairness_index: float
    estimated_co2_kg: float
    qubo_energy: float
    signal_plan: Dict[str, int]
    solver_used: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParetoFrontier:
    """Complete multi-point trade-off analysis dataset across the lambda parameter sweep.

    Attributes:
        points: Sequence of evaluated ParetoPoint records sorted by lambda.
        scenario_id: Evaluated simulation scenario identifier.
        seed: Random seed used for deterministic evaluation.
    """

    points: List[ParetoPoint]
    scenario_id: str
    seed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "points": [p.to_dict() for p in self.points],
        }


def sweep_pareto_frontier(
    scenario: SimulationScenario,
    lambda_values: Sequence[float] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    seed: int = 42,
    qaoa_p: int = 1,
    qaoa_shots: int = 1024,
) -> ParetoFrontier:
    """Compute the Pareto trade-off curve across emergency weight parameter lambda."""
    results: List[ParetoPoint] = []

    # Extract initial traffic state from scenario
    traffic_state = {
        inter: {"queue": float(scenario.initial_queues.get(inter, 10)), "density": 0.3}
        for inter in scenario.intersections
    }

    emerg_constraints = (
        scenario.emergency_config.route if scenario.emergency_config else ("I2", "I3", "I4")
    )

    for lam in lambda_values:
        lam_val = float(round(lam, 2))
        q_cfg = FullQUBOConfig(
            onehot_penalty=100.0,
            wait_weight=2.0,
            capacity_weight=10.0,
            throughput_weight=1.0,
            coupling_weight=5.0,
            emergency_weight=50.0,
            lambda_tradeoff=lam_val,
        )

        qubo = build_qubo(traffic_state, emerg_constraints, config=q_cfg)
        solve_res = solve_hybrid(qubo, emergency_constraints=emerg_constraints, qaoa_p=qaoa_p, qaoa_shots=qaoa_shots, seed=seed)

        # Simulate traffic with this signal plan
        sim = TrafficSimulator(scenario=scenario, enable_emergency_corridor=(lam_val > 0.0))
        metrics = sim.simulate(signal_plan=solve_res.plan, seed=seed)

        emissions = calculate_emissions(metrics.normal_vehicles_waiting_time)

        results.append(
            ParetoPoint(
                lambda_param=lam_val,
                emergency_response_time=metrics.emergency_response_time,
                emergency_waiting_time=metrics.emergency_waiting_time,
                civilian_waiting_time=metrics.normal_vehicles_waiting_time,
                person_delay=metrics.total_person_delay,
                throughput=metrics.throughput,
                jain_fairness_index=metrics.jain_fairness_index,
                estimated_co2_kg=emissions.estimated_co2_kg,
                qubo_energy=solve_res.energy,
                signal_plan=solve_res.plan,
                solver_used=solve_res.solver_used,
            )
        )

    return ParetoFrontier(points=results, scenario_id=scenario.scenario_id, seed=seed)
