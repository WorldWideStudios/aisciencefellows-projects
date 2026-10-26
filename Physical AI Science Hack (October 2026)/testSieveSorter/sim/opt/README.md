# Design optimizer outputs

Written by `sim/optimize.py` (the design-optimizer session, branch `design-opt`). Brief: [docs/sessions/design-optimizer.md](../../docs/sessions/design-optimizer.md).

| File | What it is | Who uses it |
|---|---|---|
| [leaderboard.md](leaderboard.md) | Demo set (pasta + chickpea / rice / quinoa): top 10, the best of each family, the fixed references, and the count matrices of the top 3 | everyone |
| [winners.json](winners.json) | The top 3, with the exact CAD constants and STRIPS / LAYERS / INSERTS lines, the sim spec and the stroke | bambu: build, render, slice |
| [LOG.md](LOG.md) | Per round: what was tried, what won, why the losers failed, the next hypothesis, and structural proposals | the next optimizer round, and anyone asking "why this design" |
| `leaderboard_insects.md`, `winners_insects.json` | The same for generated insects in BugPicker's length classes. **Exploratory**: no specimen has been measured | — |
| [leaderboard_seesaw.md](leaderboard_seesaw.md), `winners_seesaw.json` | The demo set on **the rig's motion**: each tray rocks on its own hinge across its middle, neighbours alternate (`rocking.py`), ±5–15°, with a 40 Hz buzz from round 1. Plinko rocks as one box | bambu, physics (VERIFY_SEESAW.md) |
| [leaderboard_malaise.md](leaderboard_malaise.md), `winners_malaise.json` | **EXPLORATORY:** breaker layers (`designs_breaker.py`) on the seesaw tower, ranked on a clump (`clumps.py`) for break-up, then gentleness, then sort, by `opt_malaise.py`. It uses the grain-surrogate clump until insect clumps pack | bambu (`cad/breaker_layer.py` takes the winner's `cad.spec` as is), main (PITCH.md) |

Raw runs, the search state and the `view.html` replays are under `sim/out/opt/` (gitignored).

## Reading a winner

- `sim_spec` is what the sim built, at the **as-printed** size: nominal minus 0.15 mm (an assumed undersize).
- `params_nominal` and `cad` are what goes into the CAD script, on 0.1 mm steps (0.2 mm for Z features).
- `cad.ratchet_floor_PROPOSAL`, where present, is geometry the CAD doesn't have yet; its description says what to model.
- The count matrix sums 3 friction sets x 3 seeds. Scores rank designs against each other. **They do not predict real percentages until the sim is calibrated on bench counts.**

## Running it

From `sim/` in WSL (`~/venvs/sieve/bin/python`), at most 16 workers:

```
python optimize.py plan --study demo                         # what a round costs
python optimize.py run --study demo --rounds 2               # resumes from sim/out/opt/demo/state.json and the run cache
python optimize.py run --study demo --families gated_rib     # add or continue one family
python optimize.py report --study demo                       # rebuild leaderboard / winners from the cache
python optimize.py replay --study demo --top 3               # record the winners, write view.html for each
python optimize.py run --study seesaw --families plinko,inserts --workers 12 --screen-s 10 --full-s 16 --screen-seeds 1 --full-seeds 2
python opt_malaise.py run --rounds 1 --workers 8              # EXPLORATORY clump break-up study (breaker + seesaw + buzz)
python opt_malaise.py verify --top 3 --seeds 1,2              # the leaders on freshly packed clumps
python opt_malaise.py replay --top 1                          # view.html of the winner breaking the clump
```

Seesaw and clump runs cost far more per sim second than translation runs, so those studies screen on one seed. Keep the optimizer at 12 workers in all: memory is short.
