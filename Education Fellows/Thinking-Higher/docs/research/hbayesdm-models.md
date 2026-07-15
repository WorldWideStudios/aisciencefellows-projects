# hBayesDM Model Reference (for JAX reimplementation)
Source: github.com/CCS-Lab/hBayesDM (Stan models in commons/stan_files/)

## Priority Models for ThinkHigher

### 1. Rescorla-Wagner Q-Learning (bandit2arm_delta.stan)
**Parameters (per subject, hierarchical):**
- `A` (learning rate): 0-1, how fast Q-values update
- `tau` (inverse temperature): 0-5, exploration vs exploitation

**Math:**
```
Q_init = [0, 0]
For each trial t:
  P(choice) = softmax(tau * Q)             # categorical_logit
  PE = outcome - Q[chosen]                  # prediction error
  Q[chosen] += A * PE                       # value update
```

**Hierarchical structure (non-centered / "Matt trick"):**
```
mu_pr ~ Normal(0, 1)        # group-level means (2 params)
sigma ~ Normal(0, 0.2)      # group-level SDs
A_pr[i] ~ Normal(0, 1)      # subject-level raw
tau_pr[i] ~ Normal(0, 1)
A[i] = Phi(mu_pr[1] + sigma[1] * A_pr[i])         # bounded 0-1
tau[i] = Phi(mu_pr[2] + sigma[2] * tau_pr[i]) * 5  # bounded 0-5
```

### 2. Drift-Diffusion Model (choiceRT_ddm.stan)
**Parameters (per subject, hierarchical):**
- `alpha` (boundary separation): >0, speed-accuracy tradeoff
- `beta` (initial bias): 0-1, bias toward upper/lower response
- `delta` (drift rate): unbounded, stimulus quality
- `tau` (non-decision time): bounded by RTbound and min(RT)

**Math:**
```
RT_upper ~ Wiener(alpha, tau, beta, delta)
RT_lower ~ Wiener(alpha, tau, 1-beta, -delta)
```

**Hierarchical structure:**
```
alpha = exp(mu_pr[1] + sigma[1] * alpha_pr[i])
beta = Phi(mu_pr[2] + sigma[2] * beta_pr[i])
delta = mu_pr[3] + sigma[3] * delta_pr[i]
tau = Phi(mu_pr[4] + sigma[4] * tau_pr[i]) * (minRT[i] - RTbound) + RTbound
```

### 3. RL+DDM Combined (pstRT_rlddm1.stan) -- MOST RELEVANT
From Pedersen, Frank & Biele (2017). Combines Q-learning with DDM for joint RT+choice modeling.

**Parameters:**
- `a` (boundary): >0, speed-accuracy tradeoff
- `tau` (non-decision time): bounded
- `v` (drift rate scaling): unbounded, maps Q-value difference to drift
- `alpha` (learning rate): 0-1

**Math:**
```
Q_init = matrix of initQ values
For each trial t:
  drift = (Q[condition, 1] - Q[condition, 2]) * v    # Q-diff scaled by v
  RT ~ Wiener(a, tau, 0.5, drift)                     # if upper choice
  RT ~ Wiener(a, tau, 0.5, -drift)                    # if lower choice
  Q[condition, chosen] += alpha * (feedback - Q[condition, chosen])
```

## Full Model Inventory (60+ models)
### By task:
- **Bandits**: 2arm, 4arm, Narm (delta, Kalman filter, lapse variants)
- **Go/No-Go**: gng_m1 through gng_m4
- **Iowa Gambling Task**: igt_orl, igt_pvl_decay, igt_pvl_delta, igt_vpp
- **Delay Discounting**: dd_cs, dd_exp, dd_hyperbolic
- **Probabilistic Reversal Learning**: prl_ewa, prl_fictitious (+variants)
- **Risk Aversion**: ra_noLA, ra_noRA, ra_prospect
- **Two-Step Task**: ts_par4, ts_par6, ts_par7
- **DDM (choice RT)**: choiceRT_ddm, choiceRT_lba
- **RL+DDM**: pstRT_ddm, pstRT_rlddm1, pstRT_rlddm6
- **Signal Detection**: task2AFC_sdt
- **Ultimatum Game**: ug_bayes, ug_delta
- **BART**: bart_ewmv, bart_par4

## JAX Reimplementation Notes
- Use NumPyro for MCMC (NUTS sampler, same as Stan)
- Or BlackJAX for lower-level control
- Wiener first-passage time: use `wfpt` from hddm or implement via navarro-fuss approximation
- Non-centered parameterization is critical for hierarchical models
- All models output log_lik for WAIC/LOO model comparison
