"""DMD wet-lab simulator — IV systemic AAV delivery to skeletal + cardiac muscle.

Simulated assay outputs (three per capsid):
  - muscle_transduction  : efficiency of IV systemic delivery to skeletal + cardiac muscle
  - nab_escape           : fraction of NAb panel the variant escapes
  - hepatotoxicity_score : liver off-target toxicity (clinical constraint for systemic AAV)

Calibration anchors (noise-off):
  AAV2 WT : transduction ~0.04, escape ~0.10, hepatotox ~0.15
  Muscle-tropic variant (ASSLNIA insertion, Hamming=7):
              transduction ~0.46, escape ~0.28, hepatotox ~0.26
  (Calibrated against Muller 2003, Mueller 2020, Bish 2008,
   Duan 2001, Chicoine 2014, Pfizer/ADVM hepatotox precedents.)

Inputs are sequence-level features only — same interface as AMD simulator.
In v2+ this is replaced by real IV muscle + NAb assay data; closed loop unchanged.
"""

import sys
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dmd_config as config


OUTPUTS = ["muscle_transduction", "nab_escape", "hepatotoxicity_score"]


def muscle_tropism_quality(peptide: str | None) -> float:
    """0..1 similarity to ASSLNIA muscle-targeting reference peptide.

    Analogous to peptide_quality() in AMD simulator. Measures how closely
    an insertion peptide matches the muscle-tropic motif identified in
    Muller 2003 phage-display against mouse skeletal muscle cells.
    """
    if not peptide:
        return 0.0
    return SequenceMatcher(None, peptide, config.MUSCLE_TARGET_PEPTIDE).ratio()


def fitness_penalty(hamming_to_aav2: int) -> float:
    """0..1; rises past hamming=14 (capsid folding / packaging cliff).

    Identical to AMD version — structural tolerance is capsid-independent.
    """
    excess = max(0, hamming_to_aav2 - 14)
    return float(np.tanh(excess / 6.0))


def simulate_dmd_assay(
    has_7mer_insertion: bool,
    insertion_peptide: str | None,
    insertion_length: int,
    hamming_to_aav2: int,
    noise_std: float = config.SIMULATOR_NOISE_STD,
    rng: np.random.Generator | None = None,
) -> dict:
    """Simulate IV systemic AAV assay outcomes for one capsid variant.

    Returns dict: muscle_transduction, nab_escape, hepatotoxicity_score
    (each clipped to [0, 1]) plus simulator-version metadata.

    Axis 1 — muscle_transduction:
      AAV2 WT has minimal muscle tropism via IV (~0.04).
      Muscle-targeting peptide insertions (ASSLNIA-like) boost delivery.
      VR-IV/IX substitutions that erode heparan sulfate binding (HSP)
      shift tropism from HSP-dependent liver uptake toward muscle.
      Fitness penalty dampens extreme variants.

    Axis 2 — nab_escape:
      Identical model to AMD: peptide novelty + VR-loop substitutions + synergy.
      Baseline 0.25 (AAV9-level seroprevalence reference).

    Constraint — hepatotoxicity_score:
      Liver off-target drives toxicity (TLR9 + complement activation).
      Muscle-tropic insertions REDUCE hepatotox (less liver uptake).
      Structural fitness cliff sharply increases immune risk.
    """
    if rng is None:
        rng = np.random.default_rng()

    mq = muscle_tropism_quality(insertion_peptide) if has_7mer_insertion else 0.0
    fp = fitness_penalty(hamming_to_aav2)
    fitness_factor = 1.0 - 0.6 * fp

    sub_count = (
        max(0, hamming_to_aav2 - insertion_length) if has_7mer_insertion else hamming_to_aav2
    )

    # --- Axis 1: Muscle transduction ---
    # Base = 0.04 (AAV2 IV), insertion bonus up to +0.45 (ASSLNIA-level),
    # substitutions in VR-IV/IX erode heparan binding → shift tropism to muscle.
    transduction_base   = 0.04 + 0.45 * mq
    heparan_escape_bonus = 0.18 * (1.0 - np.exp(-sub_count / 4.0))
    if has_7mer_insertion and sub_count > 0:
        tropism_synergy = 0.10 * np.tanh(mq * sub_count / 3.0)
    else:
        tropism_synergy = 0.0
    muscle_transduction = (transduction_base + heparan_escape_bonus + tropism_synergy) * fitness_factor

    # --- Axis 2: NAb escape ---
    escape_from_ins = (0.10 * mq + 0.10 * (insertion_length / 7.0)) if has_7mer_insertion else 0.0
    escape_from_subs = 0.45 * (1.0 - np.exp(-sub_count / 3.0))
    if has_7mer_insertion and sub_count > 0:
        nab_synergy = 0.15 * np.tanh(mq * sub_count / 3.0)
    else:
        nab_synergy = 0.0
    # Baseline 0.25 (approximate AAV9 seroprevalence escape reference)
    nab_escape = (0.25 + escape_from_ins + escape_from_subs + nab_synergy) * fitness_factor

    # --- Constraint: Hepatotoxicity ---
    # Structural change → complement/TLR activation (+).
    # Muscle tropism insertion → less liver uptake, less hepatotox (−).
    # Fitness cliff → severe immune response (+).
    hepatotox_from_change    = 0.10 * (1.0 - np.exp(-hamming_to_aav2 / 5.0))
    hepatotox_muscle_reduce  = -0.12 * mq   # muscle-tropic = reduced liver off-target
    hepatotox_from_cliff     = 0.40 * fp
    hepatotoxicity = max(0.0, 0.15 + hepatotox_from_change + hepatotox_muscle_reduce + hepatotox_from_cliff)

    # --- Noise ---
    muscle_transduction += rng.normal(0, noise_std)
    nab_escape          += rng.normal(0, noise_std)
    hepatotoxicity      += rng.normal(0, noise_std)

    return {
        "muscle_transduction":  float(np.clip(muscle_transduction, 0, 1)),
        "nab_escape":           float(np.clip(nab_escape, 0, 1)),
        "hepatotoxicity_score": float(np.clip(hepatotoxicity, 0, 1)),
        "_simulator_version": config.SIMULATOR_VERSION,
        "_is_simulated": True,
    }


def _sanity_check() -> None:
    """Run AAV2 WT + two synthetic anchors through simulator (noise off)."""
    rng = np.random.default_rng(0)

    aav2 = simulate_dmd_assay(False, None, 0, 0, noise_std=0.0, rng=rng)
    muscle_mimic = simulate_dmd_assay(True, config.MUSCLE_TARGET_PEPTIDE, 7, 7, noise_std=0.0, rng=rng)
    stacked = simulate_dmd_assay(True, config.MUSCLE_TARGET_PEPTIDE, 7, 12, noise_std=0.0, rng=rng)

    print("Anchors (noise off):")
    for label, r in [("AAV2 WT", aav2), ("ASSLNIA insertion (H=7)", muscle_mimic), ("Stacked (H=12)", stacked)]:
        print(
            f"  {label:<28}  transduction={r['muscle_transduction']:.3f}"
            f"  escape={r['nab_escape']:.3f}"
            f"  hepatotox={r['hepatotoxicity_score']:.3f}"
        )


if __name__ == "__main__":
    _sanity_check()
