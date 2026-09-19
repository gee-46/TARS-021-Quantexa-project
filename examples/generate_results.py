"""Regenerate results/benchmark_results*.json from the CURRENT code.

Usage:
    python examples/generate_results.py [--out-dir results]

Design (identical to the originally committed result files):
    scenario   : phase7_deterministic (canonical 12-variable QUBO, scenario seed 42)
    controllers: Fixed-Time (30s), Rule-Based Heuristic, Rule-Based (Emerg), Classical SA, Hybrid QuantumFlow
    trials     : 3 per controller, base_seed=42 -> trial seeds 84, 1084, 2084
    outputs    : benchmark_results.json (optimisation only)
                 benchmark_results_with_simulation.json (plus 300 s microscopic traffic simulation)

All quantum results come from the local Qiskit Aer SIMULATOR (QAOA p=1, 1024 shots, COBYLA maxiter 30).
No real-hardware results exist in these files. Wall-clock runtime fields vary run to run; every other
field is deterministic for the given seeds.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from optimization.benchmark import create_deterministic_scenario, run_benchmark, save_results_json
from optimization.controllers import (
    FixedTimeController,
    HybridController,
    RuleBasedController,
    SimulatedAnnealingController,
)

NUM_TRIALS = 3
BASE_SEED = 42


def build_controllers():
    return [
        FixedTimeController(name="Fixed-Time (30s)"),
        RuleBasedController(name="Rule-Based Heuristic", respect_emergency=False),
        RuleBasedController(name="Rule-Based (Emerg)", respect_emergency=True),
        SimulatedAnnealingController(name="Classical SA"),
        HybridController(name="Hybrid QuantumFlow"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "..", "results"))
    args = parser.parse_args()

    for with_sim, filename in ((False, "benchmark_results.json"), (True, "benchmark_results_with_simulation.json")):
        scenario = create_deterministic_scenario(seed=BASE_SEED, with_simulation=with_sim)
        results = run_benchmark([scenario], build_controllers(), num_trials=NUM_TRIALS, base_seed=BASE_SEED)
        path = os.path.abspath(os.path.join(args.out_dir, filename))
        save_results_json(results, path)
        print(f"wrote {path} ({len(results)} trials)")


if __name__ == "__main__":
    main()
