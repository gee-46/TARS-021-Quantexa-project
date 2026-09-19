import {
  IntersectionId,
  SignalPlan,
  SolverResult,
  EmergencyConstraints,
} from '../types/traffic';

export interface VariableInfo {
  index: number;
  intersection: IntersectionId;
  direction: IntersectionId;
  label: string;
}

export interface QUBOProblem {
  n: number;
  variables: VariableInfo[];
  groups: number[][]; // indices of variables belonging to each intersection
  linearWeights: number[]; // diagonal terms Q[i][i]
  quadraticWeights: Map<string, number>; // key "i,j" (i < j) -> Q[i][j]
  constantOffset: number;
  feasibleBitstrings: number[]; // integer indices of bitstrings that satisfy one-hot
  meta: {
    emergencyHops: [IntersectionId, IntersectionId][];
    emergencyActive: boolean;
  };
}

export class QUBOBuilder {
  // Weights (calibrated to mirror M1's QUBOConfig)
  weightService = 1.0;
  weightDownstreamDensity = 0.6;
  weightGreenWave = 0.5;
  weightMergeContention = 0.7;
  weightHysteresis = 0.2;
  weightEmergency = 15.0; // Strong priority term so corridor emerges naturally
  penaltyOneHot = 20.0;

  build(networkState: any, constraints?: EmergencyConstraints): QUBOProblem {
    const intersections = networkState.intersections;
    const roads = networkState.roads;

    const variables: VariableInfo[] = [];
    const groups: number[][] = [];
    const interToVarIndices: Map<IntersectionId, Map<IntersectionId, number>> = new Map();

    let varIdx = 0;
    for (const [interId, data] of Object.entries(intersections)) {
      const group: number[] = [];
      const dirMap = new Map<IntersectionId, number>();
      const outgoing: IntersectionId[] = (data as any).outgoing_directions || [];

      for (const dir of outgoing) {
        variables.push({
          index: varIdx,
          intersection: interId,
          direction: dir,
          label: `x_${interId}->${dir}`,
        });
        group.push(varIdx);
        dirMap.set(dir, varIdx);
        varIdx++;
      }

      groups.push(group);
      interToVarIndices.set(interId, dirMap);
    }

    const n = variables.length;
    const linearWeights = new Array(n).fill(0);
    const quadraticWeights = new Map<string, number>();
    let constantOffset = 0;

    const addQuad = (i: number, j: number, val: number) => {
      if (i === j) {
        linearWeights[i] += val;
        return;
      }
      const u = Math.min(i, j);
      const v = Math.max(i, j);
      const key = `${u},${v}`;
      quadraticWeights.set(key, (quadraticWeights.get(key) || 0) + val);
    };

    // 1. One-hot penalty for each intersection: P * (sum_d x_{i,d} - 1)^2
    // = P * (sum x_{i,d} + 2 sum_{d < d'} x_{i,d} x_{i,d'} - 2 sum x_{i,d} + 1)
    // = P * (-sum x_{i,d} + 2 sum_{d < d'} x_{i,d} x_{i,d'} + 1)
    for (const group of groups) {
      constantOffset += this.penaltyOneHot;
      for (const i of group) {
        linearWeights[i] -= this.penaltyOneHot;
      }
      for (let g1 = 0; g1 < group.length; g1++) {
        for (let g2 = g1 + 1; g2 < group.length; g2++) {
          addQuad(group[g1], group[g2], 2 * this.penaltyOneHot);
        }
      }
    }

    // 2. Service reward & downstream density discount
    for (const v of variables) {
      const interId = v.intersection;
      const targetDir = v.direction;
      const targetRoadId = `${interId}->${targetDir}`;
      const roadData = roads[targetRoadId];

      if (roadData) {
        // Find queue waiting to proceed to targetDir
        const queue = roadData.queue_length || 0;
        const capacity = roadData.capacity_per_tick || 2;
        const servicePotential = Math.min(queue, capacity);

        // Service reward (negative = lower energy)
        linearWeights[v.index] -= this.weightService * servicePotential;

        // Downstream density penalty
        const density = roadData.density || 0;
        linearWeights[v.index] += this.weightDownstreamDensity * density * servicePotential;
      }

      // Hysteresis: small cost to switch from current signal
      const currentSignal = (intersections[interId] as any).signal_state;
      if (currentSignal && currentSignal !== targetDir) {
        linearWeights[v.index] += this.weightHysteresis;
      }
    }

    // 3. Green-wave coordination: pair consecutive greens along high-traffic routes
    for (const v1 of variables) {
      const u = v1.intersection;
      const v = v1.direction;
      const vDirMap = interToVarIndices.get(v);
      if (vDirMap) {
        for (const [w, v2Idx] of vDirMap.entries()) {
          // Both (u -> v) and (v -> w) active
          addQuad(v1.index, v2Idx, -this.weightGreenWave * 0.5);
        }
      }
    }

    // 4. Emergency corridor fold-in: strong negative linear terms
    const emergencyHops: [IntersectionId, IntersectionId][] = [];
    let emergencyActive = false;

    if (constraints && constraints.active && constraints.vehicles.length > 0) {
      emergencyActive = true;
      for (const veh of constraints.vehicles) {
        const priorityFactor = (veh.priority || 100) / 100;
        for (let k = 0; k < veh.route.length - 1; k++) {
          const from = veh.route[k];
          const to = veh.route[k + 1];
          emergencyHops.push([from, to]);

          const dirMap = interToVarIndices.get(from);
          if (dirMap && dirMap.has(to)) {
            const varIdx = dirMap.get(to)!;
            // Negative linear weight guarantees ground state chooses this green direction!
            linearWeights[varIdx] -= this.weightEmergency * priorityFactor;
          }
        }
      }
    }

    // Pre-calculate feasible bitstrings (Cartesian product of groups)
    const feasibleIndices = this.computeFeasibleIndices(groups);

    return {
      n,
      variables,
      groups,
      linearWeights,
      quadraticWeights,
      constantOffset,
      feasibleBitstrings: feasibleIndices,
      meta: {
        emergencyHops,
        emergencyActive,
      },
    };
  }

  private computeFeasibleIndices(groups: number[][]): number[] {
    const feasible: number[] = [];

    const recurse = (groupIndex: number, currentMask: number) => {
      if (groupIndex === groups.length) {
        feasible.push(currentMask);
        return;
      }
      for (const bit of groups[groupIndex]) {
        recurse(groupIndex + 1, currentMask | (1 << bit));
      }
    };

    recurse(0, 0);
    return feasible;
  }

  // Energy evaluation for any bitstring (as bitmask integer)
  static evaluateEnergy(problem: QUBOProblem, bitmask: number): number {
    let energy = problem.constantOffset;

    // Linear terms
    for (let i = 0; i < problem.n; i++) {
      if ((bitmask & (1 << i)) !== 0) {
        energy += problem.linearWeights[i];
      }
    }

    // Quadratic terms
    for (const [pair, val] of problem.quadraticWeights.entries()) {
      const [uStr, vStr] = pair.split(',');
      const u = parseInt(uStr, 10);
      const v = parseInt(vStr, 10);
      if ((bitmask & (1 << u)) !== 0 && (bitmask & (1 << v)) !== 0) {
        energy += val;
      }
    }

    return energy;
  }

  // Decodes an integer bitmask into a SignalPlan
  static decodeBitmask(problem: QUBOProblem, bitmask: number): SignalPlan {
    const plan: SignalPlan = {};
    for (let i = 0; i < problem.n; i++) {
      if ((bitmask & (1 << i)) !== 0) {
        const v = problem.variables[i];
        plan[v.intersection] = v.direction;
      }
    }
    return plan;
  }
}
