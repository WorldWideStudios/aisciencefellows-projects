"""DMD closed-loop campaign driver.

Same logic as v1_release closed_loop.py with three changes:
  1. Calls dmd_wet_lab_simulator.simulate_dmd_assay() instead of simulate_wet_lab()
  2. Constraint column is hepatotoxicity_score (not inflammation_score)
  3. Pareto / HV computed on (muscle_transduction, nab_escape)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.hypervolume import Hypervolume

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DMD_ENV_ROOT = _MODULE_ROOT.parent
sys.path.insert(0, str(_MODULE_ROOT))   # finds dmd_config
sys.path.insert(0, str(_DMD_ENV_ROOT))  # finds aav_optimization package

import dmd_config as config
from aav_optimization.pipeline.dmd_world_model import OUTPUTS, DMDCapsidWorldModel
from aav_optimization.pipeline.dmd_wet_lab_simulator import simulate_dmd_assay

# Re-use policy network from v1_release
V1_PIPELINE = _DMD_ENV_ROOT.parent / "JARVIS_for_bio" / "v1_release"
sys.path.insert(0, str(V1_PIPELINE))
from pipeline.layer4_closed_loop.policy import (
    PolicyNetwork,
    gumbel_top_k_sample,
    selection_log_prob,
)

CONSTRAINT_COL = "hepatotoxicity_score"
PARETO_COLS    = ["muscle_transduction", "nab_escape"]
REF_POINT      = torch.tensor([0.0, 0.0], dtype=torch.float64)


@dataclass
class CandidatePool:
    capsid_ids: list[str]
    embeddings: np.ndarray       # (N, 2560)
    engineered: np.ndarray       # (N, 4)
    sim_inputs: list[dict]


@dataclass
class DMDCampaign:
    pool: CandidatePool
    initial_obs: pd.DataFrame
    initial_obs_embeddings: np.ndarray
    initial_obs_engineered: np.ndarray
    pca_basis: object
    rng: np.random.Generator
    constraint_threshold: float = config.HEPATOTOX_THRESHOLD
    fit_gp_hyperparameters: bool = True

    observations: pd.DataFrame = field(default_factory=pd.DataFrame)
    observation_embeddings: np.ndarray = field(default_factory=lambda: np.empty((0, 2560)))
    observation_engineered: np.ndarray = field(default_factory=lambda: np.empty((0, 4)))
    tested_ids: set = field(default_factory=set)
    hv_history: list = field(default_factory=list)

    def __post_init__(self):
        self.observations = self.initial_obs.copy()
        self.observation_embeddings = self.initial_obs_embeddings.copy()
        self.observation_engineered = self.initial_obs_engineered.copy()
        self.hv_history = [self._compute_hv(self.observations)]

    def _compute_hv(self, obs: pd.DataFrame) -> float:
        passing = obs[obs[CONSTRAINT_COL] < self.constraint_threshold]
        pts = passing[PARETO_COLS].dropna().to_numpy()
        if len(pts) == 0:
            return 0.0
        mask = _pareto_frontier_mask(pts)
        pareto = pts[mask]
        if len(pareto) == 0:
            return 0.0
        hv = Hypervolume(ref_point=REF_POINT)
        return float(hv.compute(torch.tensor(pareto, dtype=torch.float64)))

    def _refit_world_model(self) -> DMDCapsidWorldModel:
        wm = DMDCapsidWorldModel(pca_dim=16)
        wm.pca = self.pca_basis
        Y = self.observations[OUTPUTS]
        wm.fit(
            self.observation_embeddings,
            self.observation_engineered,
            Y,
            fit_hyperparameters=self.fit_gp_hyperparameters,
        )
        return wm

    def _untested_indices(self) -> np.ndarray:
        return np.array(
            [i for i, cid in enumerate(self.pool.capsid_ids) if cid not in self.tested_ids],
            dtype=int,
        )

    def _build_policy_input(
        self, untested_idx: np.ndarray, wm: DMDCapsidWorldModel
    ) -> tuple[torch.Tensor, dict]:
        emb = self.pool.embeddings[untested_idx]
        eng = self.pool.engineered[untested_idx]
        wm_x = wm.featurize(emb, eng)
        preds = wm.predict(emb, eng)
        means = np.stack([preds[o][0] for o in OUTPUTS], axis=1)
        vars_ = np.stack([preds[o][1] for o in OUTPUTS], axis=1)
        policy_x = np.concatenate([wm_x, means, vars_], axis=1)
        return torch.tensor(policy_x, dtype=torch.float32), preds

    def cycle(
        self,
        cycle_idx: int,
        policy: PolicyNetwork | None,
        k: int,
        tau: float,
        selection_strategy: str,
    ) -> dict:
        wm = self._refit_world_model()
        untested_idx = self._untested_indices()
        if len(untested_idx) < k:
            raise RuntimeError(
                f"Not enough untested candidates ({len(untested_idx)} < {k}) for cycle {cycle_idx}."
            )

        policy_x, preds = self._build_policy_input(untested_idx, wm)
        hepatotox_means = preds[CONSTRAINT_COL][0]
        passing_mask = hepatotox_means < self.constraint_threshold
        passing_local_idx = np.where(passing_mask)[0]

        if len(passing_local_idx) < k:
            order = np.argsort(hepatotox_means)
            passing_local_idx = order[: max(k, 1)]

        if policy is None:
            scores_passing = torch.tensor(
                self.rng.standard_normal(len(passing_local_idx)), dtype=torch.float32
            )
            log_p = None
            top = torch.topk(scores_passing, k).indices.tolist()
        else:
            scores_all = policy(policy_x)
            scores_passing = scores_all[passing_local_idx]
            picked_local = gumbel_top_k_sample(scores_passing, k, tau, self.rng)
            log_p = selection_log_prob(scores_passing, picked_local, tau)
            top = picked_local.tolist()

        picked_passing_local = [int(passing_local_idx[i]) for i in top]
        picked_pool_idx = [int(untested_idx[i]) for i in picked_passing_local]
        picked_ids = [self.pool.capsid_ids[i] for i in picked_pool_idx]

        outcomes = []
        n_violations = 0
        prev_hv = self.hv_history[-1]
        for pool_i in picked_pool_idx:
            si = self.pool.sim_inputs[pool_i]
            out = simulate_dmd_assay(
                has_7mer_insertion=si["has_7mer_insertion"],
                insertion_peptide=si["insertion_peptide"],
                insertion_length=si["insertion_length"],
                hamming_to_aav2=si["hamming_to_aav2"],
                rng=self.rng,
            )
            if out[CONSTRAINT_COL] >= self.constraint_threshold:
                n_violations += 1
            outcomes.append(out)

        new_rows = []
        for cid, pool_i, out in zip(picked_ids, picked_pool_idx, outcomes):
            new_rows.append({
                "capsid_id":            cid,
                "cycle":                cycle_idx,
                "selection_strategy":   selection_strategy,
                "muscle_transduction":  out["muscle_transduction"],
                "nab_escape":           out["nab_escape"],
                "hepatotoxicity_score": out["hepatotoxicity_score"],
                "meets_constraint":     out[CONSTRAINT_COL] < self.constraint_threshold,
                "source":               "wet_lab_simulator",
                "source_version":       config.SIMULATOR_VERSION,
                "is_simulated":         True,
            })
        new_obs_df = pd.DataFrame(new_rows)
        self.observations = pd.concat([self.observations, new_obs_df], ignore_index=True)
        self.observation_embeddings = np.concatenate(
            [self.observation_embeddings, self.pool.embeddings[picked_pool_idx]], axis=0
        )
        self.observation_engineered = np.concatenate(
            [self.observation_engineered, self.pool.engineered[picked_pool_idx]], axis=0
        )
        for cid in picked_ids:
            self.tested_ids.add(cid)

        new_hv = self._compute_hv(self.observations)
        self.hv_history.append(new_hv)
        reward = new_hv - prev_hv

        return {
            "cycle": cycle_idx,
            "picked_ids": picked_ids,
            "outcomes": outcomes,
            "reward": float(reward),
            "log_p": log_p,
            "prev_hv": float(prev_hv),
            "new_hv": float(new_hv),
            "n_violations": n_violations,
            "n_constraint_passing": int(passing_mask.sum()),
        }


def _pareto_frontier_mask(points: np.ndarray) -> np.ndarray:
    n = len(points)
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        p = points[i]
        is_dominated = (points >= p).all(axis=1) & (points > p).any(axis=1)
        if is_dominated.any():
            keep[i] = False
    return keep


def run_dmd_campaign(
    pool: CandidatePool,
    initial_obs: pd.DataFrame,
    initial_obs_embeddings: np.ndarray,
    initial_obs_engineered: np.ndarray,
    pca_basis: object,
    policy: PolicyNetwork | None,
    optimizer,
    rng: np.random.Generator,
    n_cycles: int = config.N_CYCLES,
    k_per_cycle: int = config.K_PER_CYCLE,
    tau: float = 1.0,
    selection_strategy: str = "rl_policy",
    fit_gp_hyperparameters: bool = True,
    reward_baseline: float = 0.0,
) -> dict:
    campaign = DMDCampaign(
        pool=pool,
        initial_obs=initial_obs,
        initial_obs_embeddings=initial_obs_embeddings,
        initial_obs_engineered=initial_obs_engineered,
        pca_basis=pca_basis,
        rng=rng,
        fit_gp_hyperparameters=fit_gp_hyperparameters,
    )

    for c in range(n_cycles):
        info = campaign.cycle(
            cycle_idx=c,
            policy=policy,
            k=k_per_cycle,
            tau=tau,
            selection_strategy=selection_strategy,
        )
        if policy is not None and optimizer is not None and info["log_p"] is not None:
            advantage = info["reward"] - reward_baseline
            loss = -torch.tensor(advantage, dtype=torch.float32) * info["log_p"]
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    return {
        "observations": campaign.observations.copy(),
        "hv_history":   list(campaign.hv_history),
        "tested_ids":   set(campaign.tested_ids),
    }
