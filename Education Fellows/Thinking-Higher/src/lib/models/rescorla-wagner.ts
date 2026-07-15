import type { BanditTrialData } from "@/lib/types";

/**
 * Compute the log-likelihood of observed choices under the Rescorla-Wagner model.
 *
 * For each trial:
 *   1. Compute softmax choice probability: P(arm_i) = exp(tau * Q[i]) / sum(exp(tau * Q[j]))
 *   2. Add log(P(chosen arm)) to total log-likelihood
 *   3. Update Q-value: Q[chosen] += alpha * (reward - Q[chosen])
 *
 * @param trials - Array of bandit trial data
 * @param alpha  - Learning rate in [0, 1]
 * @param tau    - Inverse temperature (softmax) in [0.1, 10]
 * @returns Total log-likelihood (negative; closer to 0 = better fit)
 */
export function rwLogLikelihood(
  trials: BanditTrialData[],
  alpha: number,
  tau: number
): number {
  let Q: [number, number] = [0.5, 0.5];
  let totalLL = 0;

  for (const trial of trials) {
    // Softmax choice probabilities
    const expQ0 = Math.exp(tau * Q[0]);
    const expQ1 = Math.exp(tau * Q[1]);
    const sumExp = expQ0 + expQ1;

    const pChosen =
      trial.chosenArm === 0 ? expQ0 / sumExp : expQ1 / sumExp;

    // Clamp to avoid log(0)
    totalLL += Math.log(Math.max(pChosen, 1e-15));

    // Rescorla-Wagner update
    const chosen = trial.chosenArm;
    Q = [...Q] as [number, number];
    Q[chosen] = Q[chosen] + alpha * (trial.reward - Q[chosen]);
  }

  return totalLL;
}

/**
 * Fit Rescorla-Wagner model parameters via grid search maximum likelihood estimation.
 *
 * Searches over:
 *   alpha in [0.01, 0.02, ..., 1.0]  (100 steps)
 *   tau   in [0.1,  0.2,  ..., 10.0]  (100 steps)
 *
 * Returns best-fit parameters and Q-value trajectory under those parameters.
 */
export function fitRW(trials: BanditTrialData[]): {
  alpha: number;
  tau: number;
  logLikelihood: number;
  qValuesOverTime: [number, number][];
} {
  let bestAlpha = 0.01;
  let bestTau = 0.1;
  let bestLL = -Infinity;

  // Grid search
  for (let ai = 1; ai <= 100; ai++) {
    const alpha = ai * 0.01;
    for (let ti = 1; ti <= 100; ti++) {
      const tau = ti * 0.1;
      const ll = rwLogLikelihood(trials, alpha, tau);
      if (ll > bestLL) {
        bestLL = ll;
        bestAlpha = alpha;
        bestTau = tau;
      }
    }
  }

  // Reconstruct Q-value trajectory under best-fit parameters
  const qValuesOverTime: [number, number][] = [];
  let Q: [number, number] = [0.5, 0.5];

  for (const trial of trials) {
    // Record Q-values at the start of this trial (before update)
    qValuesOverTime.push([Q[0], Q[1]]);

    // Rescorla-Wagner update
    const chosen = trial.chosenArm;
    Q = [...Q] as [number, number];
    Q[chosen] = Q[chosen] + bestAlpha * (trial.reward - Q[chosen]);
  }

  // Push final Q-values after last trial
  qValuesOverTime.push([Q[0], Q[1]]);

  return {
    alpha: Math.round(bestAlpha * 100) / 100,
    tau: Math.round(bestTau * 10) / 10,
    logLikelihood: bestLL,
    qValuesOverTime,
  };
}
