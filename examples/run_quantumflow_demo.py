"""Reproducible End-to-End QuantumFlow Demonstration Runner.

Executes a controlled comparative benchmark on the canonical Phase 15 multi-intersection scenario:
- Run A: QuantumFlow Hybrid Controller + Dynamic Emergency Green Corridor ENABLED.
- Run B: QuantumFlow Hybrid Controller + Dynamic Emergency Green Corridor DISABLED (Baseline).

Both runs utilize the identical traffic demand scenario and random seed (seed=42).
All displayed metrics and deltas are calculated dynamically from simulation executions.
"""

import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.integration import (
    create_canonical_demo_scenario,
    run_quantumflow_demo,
    compare_runs,
)


def run_demo() -> None:
    """Execute canonical QuantumFlow demo runs and display structured results."""
    scenario = create_canonical_demo_scenario(seed=42)
    seed = 42

    print("==================================================")
    print("QUANTUMFLOW END-TO-END DEMO")
    print("==================================================")
    print(f"Scenario ID: {scenario.scenario_id}")
    print(f"Simulation Duration: {scenario.duration_seconds}s | Network: {' -> '.join(scenario.intersections)}")
    print(f"Random Seed: {seed}")
    print("--------------------------------------------------")

    # RUN A: Hybrid Controller with Dynamic Green Corridor ENABLED
    print("\nExecuting RUN A: Hybrid Controller (Corridor ENABLED)...")
    result_corridor = run_quantumflow_demo(
        scenario=scenario,
        seed=seed,
        enable_emergency_corridor=True,
        controller="hybrid",
        qaoa_p=1,
        qaoa_maxiter=30,
        qaoa_shots=1024,
    )

    # RUN B: Hybrid Controller with Dynamic Green Corridor DISABLED (Baseline)
    print("Executing RUN B: Hybrid Controller (Corridor DISABLED - Baseline)...")
    result_baseline = run_quantumflow_demo(
        scenario=scenario,
        seed=seed,
        enable_emergency_corridor=False,
        controller="hybrid",
        qaoa_p=1,
        qaoa_maxiter=30,
        qaoa_shots=1024,
    )

    # Compute Factual Comparison Deltas (Run A - Run B)
    deltas = compare_runs(baseline=result_baseline, quantumflow=result_corridor)

    # Display Run A Structured Telemetry
    print("\n==================================================")
    print("RUN A TELEMETRY: QUANTUMFLOW DYNAMIC CORRIDOR")
    print("==================================================")

    print("\nNORMAL SIGNAL PLAN:")
    for inter, dur in sorted(result_corridor.normal_signal_plan.items()):
        print(f"  {inter}: {dur}s green (60s cycle)")
    print(f"Optimization Solver:     {result_corridor.optimization_solver}")
    print(f"Optimization Status:     {result_corridor.optimization_status}")
    print(f"Optimization Energy:     {result_corridor.optimization_energy:.4f}")
    print(f"Optimization Runtime:    {result_corridor.optimization_runtime:.4f}s")
    print(f"Fallback Used:           {result_corridor.optimization_fallback_used}")

    print("\nEMERGENCY TELEMETRY:")
    print(f"Emergency Present:       {result_corridor.emergency_present}")
    print(f"Emergency Detected:      t={result_corridor.emergency_detected_time}s" if result_corridor.emergency_detected_time is not None else "Emergency Detected:      None")
    print(f"Corridor Activated:      t={result_corridor.emergency_corridor_activated_time}s" if result_corridor.emergency_corridor_activated_time is not None else "Corridor Activated:      None")
    print(f"Emergency Completed:     t={result_corridor.emergency_completed_time}s" if result_corridor.emergency_completed_time is not None else "Emergency Completed:     False")
    print(f"Emergency Response Time: {result_corridor.emergency_response_time:.1f}s" if result_corridor.emergency_response_time is not None else "Emergency Response Time: N/A")
    print(f"Emergency Waiting Time:  {result_corridor.emergency_waiting_time:.1f}s" if result_corridor.emergency_waiting_time is not None else "Emergency Waiting Time:  N/A")
    print(f"Intersections Cleared:   {result_corridor.emergency_intersections_cleared}")
    print(f"Preemption Count:        {result_corridor.emergency_preemption_count}")
    print(f"Recovery Completed:      {result_corridor.recovery_completed}")

    print("\nTRAFFIC PERFORMANCE:")
    print(f"Throughput:              {result_corridor.throughput} vehicles")
    print(f"Average Waiting Time:    {result_corridor.average_waiting_time:.2f}s")
    print(f"Max Queue:               {result_corridor.max_queue} vehicles")
    print(f"Normal Vehicle Wait:     {result_corridor.normal_vehicles_waiting_time:.1f}s")

    # Display Factual Controlled Comparison Deltas
    print("\n==================================================")
    print("BASELINE VS DYNAMIC CORRIDOR DELTAS (Corridor - Baseline)")
    print("==================================================")
    resp_delta_str = f"{deltas.emergency_response_delta:+.1f}s" if deltas.emergency_response_delta is not None else "N/A"
    wait_delta_str = f"{deltas.emergency_wait_delta:+.1f}s" if deltas.emergency_wait_delta is not None else "N/A"
    print(f"Emergency Response Delta: {resp_delta_str}")
    print(f"Emergency Waiting Delta:  {wait_delta_str}")
    print(f"Normal Waiting Delta:     {deltas.normal_wait_delta:+.1f}s")
    print(f"Average Waiting Delta:    {deltas.average_wait_delta:+.2f}s")
    print(f"Throughput Delta:         {deltas.throughput_delta:+d} vehicles")
    print(f"Max Queue Delta:          {deltas.max_queue_delta:+d} vehicles")
    print(f"Preemption Delta:         {deltas.preemption_delta:+d}")
    print(f"Energy Delta:             {deltas.energy_delta:+.4f}")
    print("==================================================")


if __name__ == "__main__":
    run_demo()
