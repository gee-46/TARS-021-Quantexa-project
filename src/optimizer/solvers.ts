import { QUBOProblem, QUBOBuilder } from './qubo';
import { SolverResult, SignalPlan } from '../types/traffic';

// Interface for all solvers
export interface Solver {
  name: string;
  solve(problem: QUBOProblem): SolverResult;
}

// 1. EXACT SOLVER: Global minimum by evaluating all feasible configurations
export class ExactSolver implements Solver {
  name = 'Exact QUBO (Ground State)';

  solve(problem: QUBOProblem): SolverResult {
    const t0 = performance.now();
    let bestEnergy = Infinity;
    let bestMask = problem.feasibleBitstrings[0];

    for (const mask of problem.feasibleBitstrings) {
      const e = QUBOBuilder.evaluateEnergy(problem, mask);
      if (e < bestEnergy) {
        bestEnergy = e;
        bestMask = mask;
      }
    }

    const t1 = performance.now();
    return {
      solver: 'Exact QUBO',
      plan: QUBOBuilder.decodeBitmask(problem, bestMask),
      energy: bestEnergy,
      feasible: true,
      solveTimeMs: t1 - t0,
      info: {
        bitstring: bestMask.toString(2).padStart(problem.n, '0'),
        prob_optimal: 1.0,
        prob_feasible: 1.0,
      },
    };
  }
}

// 2. QAOA SOLVER: Quantum Approximate Optimization Algorithm (Statevector Simulation)
export interface QAOAOptions {
  p?: number; // depth
  mixer?: 'xy' | 'x';
  restarts?: number;
}

export class QAOASolver implements Solver {
  name: string;
  p: number;
  mixer: 'xy' | 'x';
  restarts: number;

  constructor(options: QAOAOptions = {}) {
    this.p = options.p ?? 3;
    this.mixer = options.mixer ?? 'xy';
    this.restarts = options.restarts ?? 2;
    this.name = `QAOA (p=${this.p}, ${this.mixer.toUpperCase()} mixer)`;
  }

  solve(problem: QUBOProblem): SolverResult {
    const t0 = performance.now();
    const n = problem.n;
    const numStates = 1 << n;

    // Fast-path protection: limit full statevector to n <= 18 qubits (our 2x3 grid is 14 qubits)
    if (n > 18) {
      throw new Error(`Statevector simulator limit is 18 qubits (received ${n})`);
    }

    // Pre-calculate energies for all states or feasible states
    const energies = new Float64Array(numStates);
    let minEnergy = Infinity;
    let maxEnergy = -Infinity;
    let groundStateMask = problem.feasibleBitstrings[0];

    for (let s = 0; s < numStates; s++) {
      const e = QUBOBuilder.evaluateEnergy(problem, s);
      energies[s] = e;
      if (problem.feasibleBitstrings.includes(s)) {
        if (e < minEnergy) {
          minEnergy = e;
          groundStateMask = s;
        }
        if (e > maxEnergy) {
          maxEnergy = e;
        }
      }
    }

    // Statevector: real and imaginary parts
    let realState = new Float64Array(numStates);
    let imagState = new Float64Array(numStates);

    // Initial state preparation
    if (this.mixer === 'xy') {
      // Uniform superposition over ONLY feasible one-hot configurations!
      const norm = 1.0 / Math.sqrt(problem.feasibleBitstrings.length);
      for (const mask of problem.feasibleBitstrings) {
        realState[mask] = norm;
      }
    } else {
      // Standard |+>^n state: uniform over ALL 2^n states
      const norm = 1.0 / Math.sqrt(numStates);
      for (let s = 0; s < numStates; s++) {
        realState[s] = norm;
      }
    }

    // Best parameters for p=3 (heuristically calibrated)
    const gammas = [0.35, 0.65, 0.95];
    const betas = [0.85, 0.55, 0.25];

    // Apply p layers of QAOA: U_C(gamma) followed by U_M(beta)
    for (let layer = 0; layer < this.p; layer++) {
      const gamma = gammas[layer % gammas.length];
      const beta = betas[layer % betas.length];

      // Cost layer: Phase separation U_C(gamma) = exp(-i * gamma * H_C)
      for (let s = 0; s < numStates; s++) {
        const theta = -gamma * energies[s];
        const cosT = Math.cos(theta);
        const sinT = Math.sin(theta);
        const r = realState[s];
        const i = imagState[s];
        realState[s] = r * cosT - i * sinT;
        imagState[s] = r * sinT + i * cosT;
      }

      // Mixer layer
      if (this.mixer === 'xy') {
        // XY mixer preserves one-hot constraint within each group
        for (const group of problem.groups) {
          for (let g1 = 0; g1 < group.length; g1++) {
            for (let g2 = g1 + 1; g2 < group.length; g2++) {
              const q1 = group[g1];
              const q2 = group[g2];
              this.applyXYGate(realState, imagState, q1, q2, beta, numStates);
            }
          }
        }
      } else {
        // Standard X mixer: single qubit rotations exp(-i * beta * X) on all qubits
        for (let q = 0; q < n; q++) {
          this.applyXGate(realState, imagState, q, beta, numStates);
        }
      }
    }

    // Compute probabilities: |psi(s)|^2
    const probs = new Float64Array(numStates);
    let totalFeasibleProb = 0;
    let groundStateProb = 0;
    let expEnergy = 0;
    let bestSampledMask = groundStateMask;
    let bestSampledProb = -1;

    for (let s = 0; s < numStates; s++) {
      const p = realState[s] * realState[s] + imagState[s] * imagState[s];
      probs[s] = p;

      const isFeasible = problem.feasibleBitstrings.includes(s);
      if (isFeasible) {
        totalFeasibleProb += p;
        if (p > bestSampledProb) {
          bestSampledProb = p;
          bestSampledMask = s;
        }
      }

      if (s === groundStateMask) {
        groundStateProb = p;
      }
      expEnergy += p * energies[s];
    }

    const approxRatio =
      maxEnergy !== minEnergy ? (maxEnergy - expEnergy) / (maxEnergy - minEnergy) : 1.0;

    const t1 = performance.now();

    return {
      solver: `QAOA (${this.mixer.toUpperCase()})`,
      plan: QUBOBuilder.decodeBitmask(problem, bestSampledMask),
      energy: energies[bestSampledMask],
      feasible: totalFeasibleProb > 0.5,
      solveTimeMs: t1 - t0,
      info: {
        p: this.p,
        mixer: this.mixer,
        prob_feasible: Math.min(1.0, totalFeasibleProb),
        prob_optimal: groundStateProb,
        uniform_prob_optimal: 1.0 / problem.feasibleBitstrings.length,
        approx_ratio: Math.max(0, Math.min(1.0, approxRatio)),
        n_evals: this.p * 2,
        bitstring: bestSampledMask.toString(2).padStart(problem.n, '0'),
      },
    };
  }

  private applyXGate(
    real: Float64Array,
    imag: Float64Array,
    qubit: number,
    beta: number,
    numStates: number
  ) {
    const mask = 1 << qubit;
    const cosB = Math.cos(beta);
    const sinB = Math.sin(beta);

    for (let s = 0; s < numStates; s++) {
      if ((s & mask) === 0) {
        const s1 = s | mask;
        const r0 = real[s];
        const i0 = imag[s];
        const r1 = real[s1];
        const i1 = imag[s1];

        // R_X(2*beta) = cos(beta)*I - i*sin(beta)*X
        real[s] = cosB * r0 + sinB * i1;
        imag[s] = cosB * i0 - sinB * r1;
        real[s1] = cosB * r1 + sinB * i0;
        imag[s1] = cosB * i1 - sinB * r0;
      }
    }
  }

  private applyXYGate(
    real: Float64Array,
    imag: Float64Array,
    q1: number,
    q2: number,
    beta: number,
    numStates: number
  ) {
    const m1 = 1 << q1;
    const m2 = 1 << q2;
    const cosB = Math.cos(beta * 0.5);
    const sinB = Math.sin(beta * 0.5);

    for (let s = 0; s < numStates; s++) {
      // Only pairs where one qubit is 1 and the other is 0
      const b1 = (s & m1) !== 0;
      const b2 = (s & m2) !== 0;

      if (b1 && !b2) {
        const partner = (s & ~m1) | m2;
        const rA = real[s];
        const iA = imag[s];
        const rB = real[partner];
        const iB = imag[partner];

        real[s] = cosB * rA + sinB * iB;
        imag[s] = cosB * iA - sinB * rB;
        real[partner] = cosB * rB + sinB * iA;
        imag[partner] = cosB * iB - sinB * rA;
      }
    }
  }
}

// 3. SIMULATED ANNEALING SOLVER
export class SimulatedAnnealingSolver implements Solver {
  name = 'Simulated Annealing';

  solve(problem: QUBOProblem): SolverResult {
    const t0 = performance.now();
    let currentMask =
      problem.feasibleBitstrings[Math.floor(Math.random() * problem.feasibleBitstrings.length)];
    let currentEnergy = QUBOBuilder.evaluateEnergy(problem, currentMask);
    let bestMask = currentMask;
    let bestEnergy = currentEnergy;

    let temp = 10.0;
    const coolingRate = 0.96;
    const steps = 300;

    for (let step = 0; step < steps; step++) {
      // Propose a random neighbor in feasible subspace (change one intersection's choice)
      const groupIdx = Math.floor(Math.random() * problem.groups.length);
      const group = problem.groups[groupIdx];
      const newBit = group[Math.floor(Math.random() * group.length)];

      let neighborMask = currentMask;
      for (const b of group) {
        neighborMask &= ~(1 << b);
      }
      neighborMask |= 1 << newBit;

      const neighborEnergy = QUBOBuilder.evaluateEnergy(problem, neighborMask);
      const delta = neighborEnergy - currentEnergy;

      if (delta < 0 || Math.random() < Math.exp(-delta / temp)) {
        currentMask = neighborMask;
        currentEnergy = neighborEnergy;
        if (currentEnergy < bestEnergy) {
          bestEnergy = currentEnergy;
          bestMask = currentMask;
        }
      }
      temp *= coolingRate;
    }

    const t1 = performance.now();
    return {
      solver: 'Simulated Annealing',
      plan: QUBOBuilder.decodeBitmask(problem, bestMask),
      energy: bestEnergy,
      feasible: true,
      solveTimeMs: t1 - t0,
      info: {
        bitstring: bestMask.toString(2).padStart(problem.n, '0'),
      },
    };
  }
}

// 4. GREEDY SOLVER
export class GreedySolver implements Solver {
  name = 'Greedy QUBO';

  solve(problem: QUBOProblem): SolverResult {
    const t0 = performance.now();
    let currentMask = 0;

    for (const group of problem.groups) {
      let bestBit = group[0];
      let lowestLinear = Infinity;
      for (const b of group) {
        if (problem.linearWeights[b] < lowestLinear) {
          lowestLinear = problem.linearWeights[b];
          bestBit = b;
        }
      }
      currentMask |= 1 << bestBit;
    }

    const energy = QUBOBuilder.evaluateEnergy(problem, currentMask);
    const t1 = performance.now();

    return {
      solver: 'Greedy QUBO',
      plan: QUBOBuilder.decodeBitmask(problem, currentMask),
      energy,
      feasible: true,
      solveTimeMs: t1 - t0,
      info: {
        bitstring: currentMask.toString(2).padStart(problem.n, '0'),
      },
    };
  }
}

// Helper: Rule-based Controller (longest queue at each intersection)
export function getRuleBasedPlan(networkState: any): SignalPlan {
  const plan: SignalPlan = {};
  for (const [interId, inter] of Object.entries(networkState.intersections) as any[]) {
    let maxQueue = -1;
    let chosen = inter.outgoing_directions[0];

    for (const outDir of inter.outgoing_directions) {
      const roadId = `${interId}->${outDir}`;
      const queue = networkState.roads[roadId]?.queue_length || 0;
      if (queue > maxQueue) {
        maxQueue = queue;
        chosen = outDir;
      }
    }
    plan[interId] = chosen;
  }
  return plan;
}
