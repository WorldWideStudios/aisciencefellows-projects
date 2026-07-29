# TODO (from pvjthomas): Plate dilution helper — extend this module to:
#   - Batch-plan stock → working plate from compound_list.json (per-compound target uM)
#   - Apply C1V1=C2V2 + 10× assay transfer rule (5 uL into 50 uL)
#   - Flag pipette-infeasible volumes (<0.5 uL) and propose serial intermediates
#     (see T1262: 10 mM → 200 uM intermediate → 10 uM working for 1 uM final)
#   - Compute matched vehicle DMSO % and warn on solubility cap (1000 uM max final)
#   - Reference: mastermix/skills/utils.py pipette limits (0.5–10 / 10–120 uL),
#     ml/agent/tools/reverse.py _recommend_screen_conc_uM(), TEM1_COLD_BLOCK_LOADING.md
# Changhu to implement when ready.

"""
Simple dilution calculator.

Setup:
  - Compound stock is at 10 mM.
  - Some volume of stock is diluted with buffer to make a "working solution".
  - 5 uL of the working solution is added to a well to make 50 uL total.
  - Given a target final concentration X (uM) in the well, compute how to
    make the working solution.
"""

import sys

STOCK_UM = 10_000       # 10 mM stock, in uM
WELL_VOLUME_UL = 50      # total volume in the well
TRANSFER_UL = 5          # volume of working solution added to the well
WORKING_VOLUME_UL = 50   # total volume of working solution to prepare


def compute_dilution(target_uM: float):
    # working solution needs to be strong enough that 5 uL into 50 uL hits target
    working_uM = target_uM * (WELL_VOLUME_UL / TRANSFER_UL)

    if working_uM > STOCK_UM:
        raise ValueError(
            f"target {target_uM} uM needs a {working_uM} uM working solution, "
            f"which is stronger than the {STOCK_UM} uM stock"
        )

    dilution_factor = STOCK_UM / working_uM
    stock_vol_uL = WORKING_VOLUME_UL / dilution_factor
    diluent_vol_uL = WORKING_VOLUME_UL - stock_vol_uL

    return {
        "target_uM": target_uM,
        "working_uM": working_uM,
        "dilution_factor": dilution_factor,
        "stock_vol_uL": stock_vol_uL,
        "diluent_vol_uL": diluent_vol_uL,
    }


if __name__ == "__main__":
    target = float(sys.argv[1])
    result = compute_dilution(target)

    print(f"Target final concentration in well: {result['target_uM']} uM")
    print(f"Working solution needed: {result['working_uM']} uM")
    print(f"Dilution factor (stock -> working): {result['dilution_factor']:.3g}x")
    print(
        f"To make {WORKING_VOLUME_UL} uL of working solution: "
        f"{result['stock_vol_uL']:.3g} uL stock + {result['diluent_vol_uL']:.3g} uL diluent"
    )
    print(
        f"Then add {TRANSFER_UL} uL of working solution to "
        f"{WELL_VOLUME_UL - TRANSFER_UL} uL other liquid -> {WELL_VOLUME_UL} uL well "
        f"at {result['target_uM']} uM"
    )
