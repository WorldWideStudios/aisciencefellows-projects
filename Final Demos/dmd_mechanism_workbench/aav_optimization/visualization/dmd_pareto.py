"""DMD capsid Pareto frontier visualization.

Reads outputs/dmd_pareto_data.parquet and writes outputs/dmd_pareto_frontier.png.

Two objectives (both maximized):
  X: muscle_transduction  — IV systemic delivery efficiency to skeletal + cardiac muscle
  Y: nab_escape           — fraction of NAb panel escaped

Constraint (filtered before plotting):
  hepatotoxicity_score < 0.40 (liver off-target safety)

Annotations mirror v1_release/visualization/pareto.py layout.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dmd_config as config

PARQUET_PATH = config.OUTPUTS_DIR / "dmd_pareto_data.parquet"
OUT_PATH     = config.OUTPUTS_DIR / "dmd_pareto_frontier.png"

# Minimum clinical thresholds (illustrative, not from a regulatory filing)
MIN_TRANSDUCTION = 0.20  # below this, IV dose would need to be impractically high
MIN_NAB_ESCAPE   = 0.40  # below this, pre-existing NAbs likely block efficacy

# Target zone on the Pareto curve
TARGET_ZONE = dict(x0=0.38, x1=0.60, y0=0.52, y1=0.72)


def theoretical_pareto_curve() -> tuple[np.ndarray, np.ndarray]:
    """Engineering trade-off envelope for IV muscle-tropic AAV.

    Control points calibrated so the curve:
      - peaks near (0, 0.90) — extreme escape-only variants
      - passes through target zone at ~(0.45, 0.60) — insertion + substitution stacks
      - drops toward (0.90, 0.10) — fitness cliff erodes escape past high Hamming
    """
    control_x = np.array([0.00, 0.10, 0.22, 0.35, 0.48, 0.60, 0.72, 0.85, 0.90])
    control_y = np.array([0.90, 0.82, 0.74, 0.66, 0.60, 0.50, 0.36, 0.20, 0.08])
    interp = PchipInterpolator(control_x, control_y)
    x = np.linspace(0.0, 0.90, 200)
    y = interp(x)
    return x, y


def main(
    parquet_path: Path = PARQUET_PATH,
    out_path: Path = OUT_PATH,
) -> None:
    df = pd.read_parquet(parquet_path)

    fig, ax = plt.subplots(figsize=(10, 8.4))

    # --- Safe therapeutic window (green shading) ---
    ax.add_patch(plt.Rectangle(
        (MIN_TRANSDUCTION, MIN_NAB_ESCAPE),
        1.02 - MIN_TRANSDUCTION, 1.02 - MIN_NAB_ESCAPE,
        facecolor="#bbf7d0", alpha=0.18, edgecolor="none", zorder=0,
    ))
    ax.text(
        0.96, 0.96, "therapeutic window\n(transduction ≥ 0.20, NAb escape ≥ 0.40)",
        color="#15803d", fontsize=9, fontweight="bold",
        ha="right", va="top", style="italic", alpha=0.75,
        transform=ax.transData,
    )

    # --- Theoretical Pareto frontier ---
    cx, cy = theoretical_pareto_curve()
    ax.plot(
        cx, cy, color="#1f5fbf", linewidth=2.2, linestyle="--",
        label="Pareto frontier (engineering trade-off)", zorder=4,
    )

    # --- Target zone ---
    tz = TARGET_ZONE
    ax.add_patch(plt.Rectangle(
        (tz["x0"], tz["y0"]), tz["x1"] - tz["x0"], tz["y1"] - tz["y0"],
        facecolor="#fef3c7", alpha=0.55, edgecolor="#a16207",
        linewidth=1.5, linestyle="-", zorder=5,
    ))
    ax.text(
        (tz["x0"] + tz["x1"]) / 2, tz["y1"] + 0.025,
        "target zone\n(strong muscle delivery\nwithin safety envelope)",
        color="#92400e", fontsize=9, fontweight="bold", ha="center", va="bottom",
        zorder=10,
    )

    # --- Constraint violations (red x's) ---
    viol = df.dropna(subset=["muscle_transduction", "nab_escape"])
    viol = viol[viol["meets_constraint"] == False]
    if len(viol) > 0:
        ax.scatter(
            viol["muscle_transduction"], viol["nab_escape"],
            s=30, c="red", alpha=0.20, marker="x",
            label=f"Hepatotoxicity ≥ {config.HEPATOTOX_THRESHOLD} (filtered)",
            zorder=2,
        )

    plot_all = df.dropna(subset=["muscle_transduction", "nab_escape"])

    # --- All evaluated candidates (grey) ---
    ax.scatter(
        plot_all["muscle_transduction"], plot_all["nab_escape"],
        s=16, c="lightgrey", alpha=0.6,
        label="All evaluated candidates", zorder=3,
    )

    # --- Random baseline ---
    rand = plot_all[plot_all["selection_strategy"] == "random_baseline"]
    ax.scatter(
        rand["muscle_transduction"], rand["nab_escape"],
        s=28, c="#9ca3af", marker="s", alpha=0.7,
        label="Random baseline picks", zorder=6,
    )

    # --- RL picks (colored by cycle) ---
    rl = plot_all[plot_all["selection_strategy"] == "rl_policy"].copy()
    if len(rl) > 0:
        sc = ax.scatter(
            rl["muscle_transduction"], rl["nab_escape"],
            s=60, c=rl["cycle"], cmap="Oranges",
            edgecolors="black", linewidths=0.7, alpha=0.95,
            label="RL policy picks", zorder=7, vmin=0, vmax=config.N_CYCLES - 1,
        )
        cb = plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label("RL cycle", fontsize=9)

    # --- Seed variants (blue squares) ---
    seed = plot_all[plot_all["selection_strategy"] == "seed"]
    if len(seed) > 0:
        ax.scatter(
            seed["muscle_transduction"], seed["nab_escape"],
            s=40, c="#3b82f6", marker="s", alpha=0.7,
            label="Seed variants (deterministic sim)", zorder=5,
        )

    # --- Threshold lines ---
    ax.axvline(MIN_TRANSDUCTION, color="grey", linestyle=":", alpha=0.6, linewidth=0.9)
    ax.axhline(MIN_NAB_ESCAPE,   color="grey", linestyle=":", alpha=0.6, linewidth=0.9)
    ax.text(MIN_TRANSDUCTION + 0.005, 1.005, f"min transduction = {MIN_TRANSDUCTION}",
            fontsize=8, color="#555555", style="italic", va="top")
    ax.text(0.005, MIN_NAB_ESCAPE - 0.005, f"min NAb escape = {MIN_NAB_ESCAPE}",
            fontsize=8, color="#555555", style="italic", va="top")

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Muscle transduction efficiency  (IV systemic — skeletal + cardiac)", fontsize=11)
    ax.set_ylabel("Neutralizing-antibody escape  (fraction of panel)", fontsize=11)
    fig.suptitle("DMD AAV Capsid Pareto Frontier",
                 fontsize=13, fontweight="bold", y=0.99)
    ax.set_title(
        "RL policy navigates muscle transduction vs NAb escape under hepatotoxicity constraint",
        fontsize=10, style="italic", pad=8,
    )
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.10),
        fontsize=9, framealpha=0.95, ncol=3, borderaxespad=0.0,
    )
    ax.grid(alpha=0.2)

    fig.text(
        0.99, 0.01,
        "Simulated data — IV muscle delivery model calibrated to Mueller 2020, Duan 2001, Chicoine 2014. "
        "AAV2 VP1 variant pool from v1_release; muscle-tropic insertion reference: ASSLNIA (Muller 2003). "
        "Pareto curve is engineering envelope, not derived from evaluated points.",
        ha="right", fontsize=7, color="#666666", style="italic",
    )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
