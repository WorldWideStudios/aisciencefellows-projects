"""DMD capsid optimization — project configuration.

Sequence/embedding assets are shared with v1_release (AAV2 VP1 variants).
Outputs land in this module's own outputs/ directory.
"""

from pathlib import Path

# --- This module root ---
MODULE_ROOT = Path(__file__).resolve().parent

# --- Shared v1_release assets (sequences + cached ESM3 embeddings) ---
V1_RELEASE = Path(__file__).resolve().parent.parent.parent / "JARVIS_for_bio" / "v1_release"
SEQUENCES_DIR   = V1_RELEASE / "data" / "sequences"
EMBEDDINGS_DIR  = V1_RELEASE / "data" / "embeddings" / "esm3"
EMBEDDINGS_INDEX = EMBEDDINGS_DIR / "index.parquet"
PRETRAINED_POLICY = V1_RELEASE / "data" / "pretrained_policy.pt"

AAV2_FASTA            = SEQUENCES_DIR / "aav2_vp1_wildtype.fasta"
AAV7M8_FASTA          = SEQUENCES_DIR / "aav7m8_vp1_reference.fasta"
CAPSID_VARIANTS_FASTA = SEQUENCES_DIR / "capsid_variants.fasta"

# --- DMD outputs ---
OUTPUTS_DIR = MODULE_ROOT / "outputs"
RESULTS_DB  = MODULE_ROOT / "outputs" / "dmd_results.db"

# --- AAV VR loops (AAV2 VP1, 1-indexed) — shared with v1 ---
VR_LOOPS = {
    "VR-I":    (263, 268),
    "VR-IV":   (449, 468),
    "VR-V":    (488, 505),
    "VR-VIII": (581, 593),
    "VR-IX":   (704, 714),
}
SUBSTITUTION_LOOPS        = ["VR-IV", "VR-V", "VR-VIII", "VR-IX"]
STACKED_SUBSTITUTION_LOOPS = ["VR-IV", "VR-V", "VR-IX"]
INSERTION_AFTER_RESIDUE   = 587

# --- DMD simulator parameters ---
# Calibrated to IV systemic AAV muscle delivery literature:
#   AAV9:    muscle_transduction ~0.55, nab_escape ~0.25, hepatotox ~0.30
#     (Mueller 2020, Bish 2008, Vandendriessche 2007)
#   AAVrh74: muscle_transduction ~0.50, nab_escape ~0.45, hepatotox ~0.20
#     (Duan 2001, Chicoine 2014 — lower human seroprevalence than AAV9)
#   AAV2 WT: muscle_transduction ~0.04 (poor IV muscle — no muscle tropism motif)

# Reference muscle-targeting peptide (Muller 2003 Nat Biotechnol phage display).
# Analogous role to LALGETTRP in AMD / retinal-targeting.
MUSCLE_TARGET_PEPTIDE   = "ASSLNIA"

HEPATOTOX_THRESHOLD     = 0.40      # max acceptable (same scale as inflammation in v1)
SIMULATOR_NOISE_STD     = 0.08
SIMULATOR_VERSION       = "dmd_sim_v1.0"

# --- Closed-loop hyperparameters ---
N_CYCLES    = 10
K_PER_CYCLE = 5
N_SEED_VARIANTS = 12    # variants from pool used to seed the initial world model
RNG_SEED    = 2026
