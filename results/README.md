# Benchmark results

Regenerate with the current code (Python 3.10-3.13, pinned `requirements.txt`):

```bash
python examples/generate_results.py
```

| File | Contents |
|---|---|
| `benchmark_results.json` | Optimisation-only results: scenario `phase7_deterministic`, 5 controllers x 3 trials |
| `benchmark_results_with_simulation.json` | Same plus the 300 s microscopic traffic simulation (person-delay, Jain fairness, CO2) |

Settings: scenario seed 42, `base_seed=42`, trial seeds 84 / 1084 / 2084, Hybrid QuantumFlow = QAOA p=1, 1024 shots, COBYLA maxiter 30 (SA fallback).

**Provenance: every result here comes from the local Qiskit Aer *simulator*. There are no real-hardware results in this repository.**

Reproducibility: two consecutive regenerations are identical except the wall-clock `runtime_seconds` fields. Results depend on the pinned library versions; QAOA sampling outcomes were observed to differ between library environments (the previous committed files came from an older environment), so regenerate rather than compare across environments.
