"""Standardized Benchmark Metrics and Statistical Aggregation for QuantumFlow.

Explicitly separates:
1. Optimization Metrics (QUBO energy, runtime, fallback occurrence, solver used, optimality gap)
2. Traffic Metrics (waiting time, throughput, queue length, emergency delay - marked unavailable if simulator is not active).

Provides dataclasses, serialization to/from dictionaries, and descriptive statistical summaries (mean, median, std, min, max).
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional, Sequence
import numpy as np


@dataclass(frozen=True)
class OptimizationMetrics:
    """Quantitative metrics evaluating the mathematical optimization process."""

    status: str
    runtime_seconds: float
    qubo_energy: float
    best_bitstring: str
    fallback_used: Optional[bool] = None
    fallback_reason: Optional[str] = None
    solver_used: Optional[str] = None
    onehot_valid: bool = True
    emergency_valid: bool = True
    exact_optimum_energy: Optional[float] = None
    optimality_gap: Optional[float] = None
    exact_optimum_found: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationMetrics":
        return cls(**data)


@dataclass(frozen=True)
class TrafficMetrics:
    """Traffic simulation metrics evaluating network performance outcomes.

    Note: All metrics remain None/unavailable when evaluating optimization without a simulator.
    """

    available: bool = False
    total_waiting_time: Optional[float] = None
    average_waiting_time: Optional[float] = None
    max_queue: Optional[float] = None
    average_queue: Optional[float] = None
    throughput: Optional[float] = None
    emergency_response_time: Optional[float] = None
    emergency_delay: Optional[float] = None
    person_delay: Optional[float] = None
    jain_fairness_index: Optional[float] = None
    max_approach_wait: Optional[float] = None
    starvation_violations: Optional[float] = None
    idle_vehicle_seconds: Optional[float] = None
    estimated_fuel_liters: Optional[float] = None
    estimated_co2_kg: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrafficMetrics":
        return cls(**data)



@dataclass(frozen=True)
class TrialResult:
    """Single trial execution result for one controller on one scenario."""

    scenario_id: str
    trial_index: int
    seed: int
    controller_name: str
    signal_plan: Dict[str, int]
    optimization_metrics: OptimizationMetrics
    traffic_metrics: TrafficMetrics = field(default_factory=TrafficMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "trial_index": self.trial_index,
            "seed": self.seed,
            "controller_name": self.controller_name,
            "signal_plan": self.signal_plan,
            "optimization_metrics": self.optimization_metrics.to_dict(),
            "traffic_metrics": self.traffic_metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrialResult":
        return cls(
            scenario_id=data["scenario_id"],
            trial_index=data["trial_index"],
            seed=data["seed"],
            controller_name=data["controller_name"],
            signal_plan=data["signal_plan"],
            optimization_metrics=OptimizationMetrics.from_dict(data["optimization_metrics"]),
            traffic_metrics=TrafficMetrics.from_dict(data.get("traffic_metrics", {})),
        )


@dataclass(frozen=True)
class MetricSummary:
    """Descriptive statistics for a numerical metric across multiple trials."""

    metric_name: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_metric_summary(values: Sequence[float], metric_name: str) -> MetricSummary:
    """Calculate mean, median, std, min, max for a sequence of numbers.

    Args:
        values: Sequence of numeric values.
        metric_name: Name of the metric being summarized.

    Returns:
        MetricSummary: Computed statistical distribution.
    """
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0:
        return MetricSummary(
            metric_name=metric_name,
            count=0,
            mean=0.0,
            median=0.0,
            std=0.0,
            min=0.0,
            max=0.0,
        )

    return MetricSummary(
        metric_name=metric_name,
        count=int(len(arr)),
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        std=float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        min=float(np.min(arr)),
        max=float(np.max(arr)),
    )


def summarize_results(results: Sequence[TrialResult]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Aggregate benchmark results grouped by (scenario_id, controller_name).

    Args:
        results: Sequence of TrialResult records.

    Returns:
        Dict: Structured dictionary with descriptive statistics per controller.
    """
    grouped: Dict[Tuple[str, str], List[TrialResult]] = {}
    for r in results:
        key = (r.scenario_id, r.controller_name)
        grouped.setdefault(key, []).append(r)

    summary: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for (scen_id, ctrl_name), group in grouped.items():
        if scen_id not in summary:
            summary[scen_id] = {}

        energies = [t.optimization_metrics.qubo_energy for t in group if np.isfinite(t.optimization_metrics.qubo_energy)]
        runtimes = [t.optimization_metrics.runtime_seconds for t in group]
        gaps = [
            t.optimization_metrics.optimality_gap
            for t in group
            if t.optimization_metrics.optimality_gap is not None and np.isfinite(t.optimization_metrics.optimality_gap)
        ]

        fallback_count = sum(1 for t in group if t.optimization_metrics.fallback_used is True)
        valid_onehot_count = sum(1 for t in group if t.optimization_metrics.onehot_valid)
        valid_emergency_count = sum(1 for t in group if t.optimization_metrics.emergency_valid)

        traffic_avail = any(t.traffic_metrics.available for t in group)
        traffic_summary = None
        if traffic_avail:
            waits = [t.traffic_metrics.total_waiting_time for t in group if t.traffic_metrics.total_waiting_time is not None]
            avg_waits = [t.traffic_metrics.average_waiting_time for t in group if t.traffic_metrics.average_waiting_time is not None]
            throughputs = [t.traffic_metrics.throughput for t in group if t.traffic_metrics.throughput is not None]
            max_qs = [t.traffic_metrics.max_queue for t in group if t.traffic_metrics.max_queue is not None]
            avg_qs = [t.traffic_metrics.average_queue for t in group if t.traffic_metrics.average_queue is not None]
            emerg_resps = [t.traffic_metrics.emergency_response_time for t in group if t.traffic_metrics.emergency_response_time is not None]

            traffic_summary = {
                "total_waiting_time": calculate_metric_summary(waits, "total_waiting_time").to_dict() if waits else None,
                "average_waiting_time": calculate_metric_summary(avg_waits, "average_waiting_time").to_dict() if avg_waits else None,
                "throughput": calculate_metric_summary(throughputs, "throughput").to_dict() if throughputs else None,
                "max_queue": calculate_metric_summary(max_qs, "max_queue").to_dict() if max_qs else None,
                "average_queue": calculate_metric_summary(avg_qs, "average_queue").to_dict() if avg_qs else None,
                "emergency_response_time": calculate_metric_summary(emerg_resps, "emergency_response_time").to_dict() if emerg_resps else None,
            }

        ctrl_summary = {
            "num_trials": len(group),
            "qubo_energy": calculate_metric_summary(energies, "qubo_energy").to_dict(),
            "runtime_seconds": calculate_metric_summary(runtimes, "runtime_seconds").to_dict(),
            "optimality_gap": calculate_metric_summary(gaps, "optimality_gap").to_dict() if gaps else None,
            "fallback_count": fallback_count,
            "valid_onehot_count": valid_onehot_count,
            "valid_emergency_count": valid_emergency_count,
            "traffic_metrics_available": traffic_avail,
            "traffic_metrics": traffic_summary,
        }

        summary[scen_id][ctrl_name] = ctrl_summary

    return summary

