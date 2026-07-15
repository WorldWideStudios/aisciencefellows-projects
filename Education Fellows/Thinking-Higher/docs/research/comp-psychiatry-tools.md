# Computational Psychiatry Tools & Resources

## Source: CPC Zurich (translationalneuromodeling.org/cpcourse)
ETH Zurich / University of Zurich course, running since 2015. Materials at github.com/computational-psychiatry-course

## Core Toolboxes (by relevance to ThinkHigher)

### HIGH PRIORITY — JAX-compatible or portable

**pyhgf (Hierarchical Gaussian Filter) — JAX-NATIVE**
- Repo: github.com/ilabcode/pyhgf
- Language: Python + JAX (JIT-compiled, differentiable)
- What: Bayesian filtering for belief updating under uncertainty
- Model: Nodes encode Gaussian distributions. New observations trigger recursive update via top-down predictions + bottom-up precision-weighted prediction errors.
- Use for ThinkHigher: Model how participants update beliefs about task structure across stages. Tracks uncertainty and learning in real-time. Can detect when a participant's belief update is abnormal (too rigid or too volatile).
- Paper: Weber et al. (2024)
- DIRECTLY COMPATIBLE with our JAX/NumPyro stack

**hBayesDM (hierarchical Bayesian Decision-Making)**
- Repo: github.com/CCS-Lab/hBayesDM
- Language: R + Python (Stan backend)
- What: 60+ computational cognitive models for decision tasks
- Models: Q-learning, DDM, RL+DDM, IGT, delay discounting, Go/No-Go, etc.
- Full math documented in `hbayesdm-models.md`
- Reimplement in JAX/NumPyro for our stack

**HMeta-d (Hierarchical Metacognitive Efficiency)**
- Repo: github.com/metacoglab/HMeta-d
- Language: MATLAB + R (JAGS backend)
- What: Quantifies metacognitive efficiency — how well people judge accuracy of their own decisions
- Model: Extends Signal Detection Theory (SDT) to metacognitive domain
- Functions: fit_meta_d_mcmc (individual), fit_meta_d_mcmc_group (hierarchical)
- Use for ThinkHigher: Measure whether participants know when they're performing well vs poorly in the simulation. Can we detect metacognitive deficits from conversational behavior?
- Needs JAX reimplementation (port from JAGS)

### HIGH PRIORITY — JAX sampling & DDM infrastructure

**BlackJAX (JAX Sampling Library)**
- Repo: github.com/blackjax-devs/blackjax
- Language: Python + JAX
- What: Composable MCMC/SMC sampling library built on JAX. Lower-level than NumPyro — exposes building blocks.
- Samplers: NUTS, HMC, SMC, MALA, elliptical slice, tempered SMC, variational inference (meanfield, fullrank)
- Architecture: Kernel-based — `init_fn(position) → state`, `kernel(rng_key, state) → new_state, info`
- GPU/TPU native, JIT-compiled, fully differentiable
- Use for ThinkHigher: Custom samplers for cognitive models that don't fit standard NumPyro patterns. Fine-grained control over MCMC tuning. Can combine with NumPyro models or standalone.
- Complements NumPyro: NumPyro for rapid prototyping, BlackJAX for production/custom inference

**HDDM (Hierarchical Drift-Diffusion Model) — Brown University**
- Repo: github.com/hddm-devs/hddm
- Language: Python (PyMC 2.3.8 backend)
- What: Gold-standard hierarchical DDM fitting. 400+ published papers using it.
- Parameters: v (drift rate), a (boundary separation), t (non-decision time), z (starting point bias)
- Key variants:
  - **HDDMnn**: Neural network likelihoods — flexible sequential sampling models beyond standard DDM
  - **HDDMrl**: RL+DDM integration — joint fitting of learning and decision parameters
  - **HDDMRegression**: Trial-level regressors on DDM parameters (e.g., condition effects on drift rate)
- Use for ThinkHigher: Reference implementation for DDM models. Port math to JAX/NumPyro. HDDMrl is closest to our pstRT_rlddm1 target.
- Note: Pinned to PyMC 2.3.8 (legacy). Do NOT install directly — reimplement core math in NumPyro/BlackJAX.
- Paper: Wiecki, Sofer & Frank (2013), Frontiers in Neuroinformatics

### MEDIUM PRIORITY — Useful concepts, partial portability

**VBA-toolbox (Variational Bayesian Analysis)**
- Site: mbb-team.github.io/VBA-toolbox
- Language: MATLAB
- What: General framework for model inversion via variational Bayes
- Use: Alternative to MCMC — faster approximate inference. Could use for real-time model fitting (variational inference in JAX is faster than MCMC)

**PCNtoolkit (Predictive Clinical Neuroscience)**
- Repo: github.com/predictive-clinical-neuroscience/PCNtoolkit-demo
- Language: Python
- What: Normative modeling — establish "normal range" of behavior, then identify deviations
- Use for ThinkHigher: Build normative models from Prolific population data, then flag individual participants whose cognitive profile deviates significantly

**RegressionDCM.jl (Regression Dynamic Causal Modeling)**
- Repo: github.com/ComputationalPsychiatry/RegressionDynamicCausalModeling.jl
- Language: Julia
- What: Efficient directed connectivity estimation from fMRI
- Part of TAPAS framework (Translational Neuromodeling)
- Lower priority for ThinkHigher (we don't have neuroimaging data), but the directed connectivity concept could apply to modeling information flow between conversation stages

### LOWER PRIORITY — Neuroimaging-specific

**SPM12** — Active inference, DCM for EEG/fMRI (MATLAB). Relevant if we add EEG/webcam-based physiological measures.
**NeuroMiner** — ML for precision psychiatry (MATLAB). Classification/prediction from multimodal data.

## Key Concepts from CPC Curriculum

### Day 2-4 Topics (most relevant):
1. **Model fitting and selection** — Bayesian model comparison (BIC, WAIC, LOO)
2. **Reinforcement learning** — Q-learning, Rescorla-Wagner, hierarchical Bayesian
3. **Predictive coding** — Brain as prediction machine, prediction error minimization
4. **HGF** — Hierarchical belief updating under uncertainty (JAX-native via pyhgf!)
5. **Action selection** — MDPs, active inference, drift-diffusion models
6. **Metacognition** — Can the participant judge their own performance?
7. **Machine learning** — Normative modeling, classification of cognitive profiles

### Mathematical Foundations (from precourse prep):
- Linear algebra, calculus, differential equations
- Bayesian statistics (van de Schoot et al., 2021, Nature Reviews Methods Primers)
- Signal detection theory (for metacognition)
- Markov decision processes (for action selection)

## TCP Lab CompPsych
- URL: tcplab.org/comppsych
- Additional computational psychiatry materials (Google Sites page, content not directly fetchable)

## Integration Plan for ThinkHigher

### Immediate (JAX stack):
1. **pyhgf** — Import directly. Model belief updating across scenario stages.
2. **hBayesDM models** — Reimplement RW, DDM, RL+DDM in NumPyro (math in hbayesdm-models.md)
3. **Normative modeling** — Build population baselines from Prolific data, flag deviations

### Medium-term:
4. **Metacognition (HMeta-d)** — Port to NumPyro. Add confidence ratings to post-stage surveys.
5. **Variational inference** — For real-time model fitting (faster than MCMC, viable during session)

### Long-term:
6. **Active inference** — Model participants as active inference agents, compare to actual behavior
7. **Predictive coding** — Framework for understanding RT patterns as prediction error signals
