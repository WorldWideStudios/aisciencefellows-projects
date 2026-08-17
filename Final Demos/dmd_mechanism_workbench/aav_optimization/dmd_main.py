"""DMD AAV capsid optimization pipeline — end-to-end runner.

Uses the v1_release candidate pool (120 AAV2 VP1 variants + 2 anchors),
their cached ESM3 embeddings, and the pretrained RL policy. Adapts the
simulation to DMD-relevant IV systemic muscle delivery.

Steps:
  1. Load pool from v1_release FASTA + embedding index
  2. Seed world model with N_SEED_VARIANTS deterministic simulator runs
  3. Run RL campaign + random baseline campaign
  4. Export outputs/dmd_pareto_data.parquet + dmd_results.db
  5. Render visualization with:  python visualization/dmd_pareto.py
"""

import sys
import gc
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from Bio import SeqIO
from difflib import SequenceMatcher

MODULE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_ROOT))
import dmd_config as config

# v1_release helpers (pool loader, PCA, policy loading)
V1_RELEASE = config.V1_RELEASE
sys.path.insert(0, str(V1_RELEASE))
from scripts.pretrain_policy import load_pca_basis, load_pool
from pipeline.layer4_closed_loop.policy import PolicyNetwork

# DMD-specific pipeline (must come after sys.path setup)
sys.path.insert(0, str(MODULE_ROOT))
from aav_optimization.pipeline.dmd_world_model import OUTPUTS, DMDCapsidWorldModel
from aav_optimization.pipeline.dmd_wet_lab_simulator import simulate_dmd_assay
from aav_optimization.pipeline.dmd_closed_loop import CandidatePool, run_dmd_campaign, _pareto_frontier_mask


# --------------------------------------------------------------------------- helpers


def _peptide_quality(peptide: str | None, ref: str) -> float:
    if not peptide:
        return 0.0
    return SequenceMatcher(None, peptide, ref).ratio()


def _seed_initial_obs(
    pool: CandidatePool,
    n: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Run the DMD simulator (noise off) on n deterministic pool samples to seed the GP."""
    idx = rng.choice(len(pool.capsid_ids), size=min(n, len(pool.capsid_ids)), replace=False)
    rows = []
    for i in idx:
        si = pool.sim_inputs[i]
        out = simulate_dmd_assay(
            has_7mer_insertion=si["has_7mer_insertion"],
            insertion_peptide=si["insertion_peptide"],
            insertion_length=si["insertion_length"],
            hamming_to_aav2=si["hamming_to_aav2"],
            noise_std=0.0,
            rng=rng,
        )
        rows.append({
            "capsid_id":            pool.capsid_ids[i],
            "cycle":                -1,
            "selection_strategy":   "seed",
            "muscle_transduction":  out["muscle_transduction"],
            "nab_escape":           out["nab_escape"],
            "hepatotoxicity_score": out["hepatotoxicity_score"],
            "meets_constraint":     out["hepatotoxicity_score"] < config.HEPATOTOX_THRESHOLD,
            "source":               "seed_sim",
            "source_version":       config.SIMULATOR_VERSION,
            "is_simulated":         True,
        })
    return pd.DataFrame(rows)


def _pareto_mask_2d(points: np.ndarray) -> np.ndarray:
    n = len(points)
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        p = points[i]
        dominated = (points >= p).all(axis=1) & (points > p).any(axis=1)
        if dominated.any():
            keep[i] = False
    return keep


def stamp_pareto_frontier(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    out["is_on_pareto_frontier"] = False
    seed_mask = out["selection_strategy"] == "seed"
    for strat in out["selection_strategy"].unique():
        if strat == "seed":
            continue
        rel = out[(out["selection_strategy"] == strat) | seed_mask].copy()
        rel = rel[rel["meets_constraint"] == True].copy()
        rel = rel.dropna(subset=["muscle_transduction", "nab_escape"])
        if len(rel) == 0:
            continue
        pts  = rel[["muscle_transduction", "nab_escape"]].to_numpy()
        keep = _pareto_mask_2d(pts)
        out.loc[rel.index[keep], "is_on_pareto_frontier"] = True
    return out


# --------------------------------------------------------------------------- main


def main(seed: int = config.RNG_SEED) -> None:
    print("=== DMD AAV Capsid Optimization Pipeline (v1) ===\n")
    rng = np.random.default_rng(seed)

    # --- Load pool from v1_release ---
    print("[1/5] Loading candidate pool + embeddings from v1_release...")
    pool_v1 = load_pool()                              # CandidatePool (v1 type)
    idx_df  = pd.read_parquet(config.EMBEDDINGS_INDEX)

    # Repackage as DMD CandidatePool
    pool = CandidatePool(
        capsid_ids=pool_v1.capsid_ids,
        embeddings=pool_v1.embeddings,
        engineered=pool_v1.engineered,
        sim_inputs=pool_v1.sim_inputs,
    )
    print(f"  candidate pool: {len(pool.capsid_ids)}")

    # --- Fit PCA on the full embedding cache ---
    pca = load_pca_basis()
    print(f"  PCA basis: {pca.n_components_} components")

    # --- Seed initial observations ---
    print(f"[2/5] Seeding world model with {config.N_SEED_VARIANTS} deterministic simulator runs...")
    obs0 = _seed_initial_obs(pool, config.N_SEED_VARIANTS, rng)
    seed_ids = set(obs0["capsid_id"])

    # Build embedding/engineered arrays matching obs0 row order
    cid_to_idx = {cid: i for i, cid in enumerate(pool.capsid_ids)}
    seed_pool_idx = [cid_to_idx[cid] for cid in obs0["capsid_id"] if cid in cid_to_idx]
    obs0_emb = pool.embeddings[seed_pool_idx]
    obs0_eng = pool.engineered[seed_pool_idx]
    print(f"  seeded {len(obs0)} variants")

    # --- Load pretrained policy ---
    print("[3/5] Loading pretrained RL policy from v1_release...")
    ckpt   = torch.load(config.PRETRAINED_POLICY, weights_only=False)
    policy = PolicyNetwork(input_dim=ckpt["input_dim"])
    policy.load_state_dict(ckpt["state_dict"])
    policy.eval()
    for p in policy.parameters():
        p.requires_grad_(False)
    print(f"  policy: {policy.num_parameters():,} params, pretrained {ckpt['n_campaigns']} AMD campaigns")
    print("  (transferred to DMD — REINFORCE will adapt during the campaign)")

    # --- Run RL + random campaigns ---
    print(f"[4/5] Running RL + random campaigns ({config.N_CYCLES} cycles, k={config.K_PER_CYCLE})...")
    t0 = time.time()
    with torch.no_grad():
        rl_result = run_dmd_campaign(
            pool=pool, initial_obs=obs0,
            initial_obs_embeddings=obs0_emb, initial_obs_engineered=obs0_eng,
            pca_basis=pca, policy=policy, optimizer=None,
            rng=np.random.default_rng(seed),
            n_cycles=config.N_CYCLES, k_per_cycle=config.K_PER_CYCLE,
            tau=ckpt["tau"], selection_strategy="rl_policy",
            fit_gp_hyperparameters=False, reward_baseline=0.0,
        )
        gc.collect()
        rand_result = run_dmd_campaign(
            pool=pool, initial_obs=obs0,
            initial_obs_embeddings=obs0_emb, initial_obs_engineered=obs0_eng,
            pca_basis=pca, policy=None, optimizer=None,
            rng=np.random.default_rng(seed),
            n_cycles=config.N_CYCLES, k_per_cycle=config.K_PER_CYCLE,
            tau=ckpt["tau"], selection_strategy="random_baseline",
            fit_gp_hyperparameters=False, reward_baseline=0.0,
        )
    print(f"  ran in {time.time()-t0:.1f}s")
    print(f"  RL    final HV = {rl_result['hv_history'][-1]:.4f}")
    print(f"  random final HV = {rand_result['hv_history'][-1]:.4f}")

    # --- Build full results table ---
    def campaign_rows(obs: pd.DataFrame, strategy: str) -> pd.DataFrame:
        df = obs[obs["source"] == "wet_lab_simulator"].copy()
        df["selection_strategy"] = strategy
        df["is_on_pareto_frontier"] = False
        return df

    all_results = pd.concat([
        obs0.assign(is_on_pareto_frontier=False),
        campaign_rows(rl_result["observations"],   "rl_policy"),
        campaign_rows(rand_result["observations"], "random_baseline"),
    ], ignore_index=True)
    all_results = stamp_pareto_frontier(all_results)

    # --- Export ---
    print("[5/5] Exporting outputs/...")
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    pareto_df = all_results[all_results["is_on_pareto_frontier"]].copy()
    # Write pareto data (RL-selected + constraint-passing candidates)
    all_results.to_parquet(config.OUTPUTS_DIR / "dmd_pareto_data.parquet", index=False)
    pareto_df.to_parquet(config.OUTPUTS_DIR / "dmd_pareto_frontier.parquet", index=False)

    print(f"  outputs/dmd_pareto_data.parquet    ({len(all_results)} rows)")
    print(f"  outputs/dmd_pareto_frontier.parquet ({len(pareto_df)} Pareto-optimal rows)")

    # Cycle summary
    rl_cyc = rl_result["observations"][rl_result["observations"]["source"] == "wet_lab_simulator"]
    print(f"\nRL campaign:")
    print(f"  variants tested:            {len(rl_result['tested_ids'])}")
    print(f"  constraint-passing (hepatotox < {config.HEPATOTOX_THRESHOLD}): "
          f"{(rl_cyc['meets_constraint'] == True).sum()}")
    print(f"  top muscle_transduction:    {rl_cyc['muscle_transduction'].max():.3f}")
    print(f"  top nab_escape:             {rl_cyc['nab_escape'].max():.3f}")
    print(f"  Pareto-optimal RL variants: {(pareto_df['selection_strategy']=='rl_policy').sum()}")

    print("\nDone. Render the Pareto figure with:")
    print("  cd /home/ubuntu/dmd_inference_env/aav_optimization")
    print("  python visualization/dmd_pareto.py")
    print("\nThen run hypothesis mapping with:")
    print("  python hypothesis_mapping.py")


if __name__ == "__main__":
    main()
