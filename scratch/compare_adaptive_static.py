import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from simulation.integration import run_adaptive_vs_static_comparison

comp = run_adaptive_vs_static_comparison(seed=42, replan_interval=60, enable_emergency_corridor=True)
print("=== SUMMARY ===")
print(json.dumps(comp["summary"], indent=2))
print("=== ADAPTIVE REPLANNING EVENTS ===")
print(json.dumps(comp["adaptive"]["replanning_events"], indent=2))
print("=== STATS ===")
print(f"Static Throughput: {comp['static']['throughput']}")
print(f"Adaptive Throughput: {comp['adaptive']['throughput']}")
print(f"Static Avg Wait: {comp['static']['average_waiting_time']:.2f}")
print(f"Adaptive Avg Wait: {comp['adaptive']['average_waiting_time']:.2f}")
print(f"Static Max Queue: {comp['static']['max_queue']}")
print(f"Adaptive Max Queue: {comp['adaptive']['max_queue']}")
print(f"Cumulative Opt Runtime: {comp['adaptive']['cumulative_optimization_runtime']:.4f}s")
print(f"QAOA Executions: {comp['adaptive']['qaoa_execution_count']}")
print(f"SA Fallbacks: {comp['adaptive']['sa_fallback_count']}")
