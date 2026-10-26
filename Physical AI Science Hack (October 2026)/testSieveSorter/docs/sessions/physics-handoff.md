# Handoff: physics session (prompting mode) to a bypass-permissions session

> **Read [docs/SYSTEM.md](../SYSTEM.md) first** (added 10:30). It's the one description of the system: the input is a clump; the rig is separate trays one above the other, each held at its +X tab and overhanging, so they **rock**. It overrides this brief where they differ.

Written 2026-10-25 06:15 PT by the main session. The first physics session ran in prompting mode and kept stopping for approvals. After its write-up landed, it was closed, and a session in bypass mode took over the same worktree (`testSieveSorter-physics`, branch `physics-bench`). Briefs: [physics.md](physics.md), [demo-rig.md](demo-rig.md) parts A and B (both done).

## Done and on `main`
- **PR #2:**
  - **`angle_deg`** on the stroke: 0 = along the flow axis, 90 = straight up.
  - **`inserts:5mm`**, the single-insert demo tray.
  - **Unstable runs are flagged:** `results["unstable_resets"]`, and the sweep log tags them.
  - `instab.py`, `sweep.py --workers`, `stroke_from_video.py` (self-tested; Forum's clip shows the tool idle).
  - The WSL notes in [README.md](README.md).
- **PR #3:**
  - [`sim/VERTICAL.md`](../../sim/VERTICAL.md):
    - All directions sort the demo mix at 1.00.
    - Along the flow axis clears the last rice 2–3x faster than straight up.
    - 45° is worst under heavy load.
    - Gates with clearance under 0.3 mm need dt 0.125 ms / tc 0.25 ms for vertical strokes.
  - [`sim/PERF.md`](../../sim/PERF.md): 45 s vs 517 s for the reference run, and worker scaling.
  - The `sweep.py vertical` preset.

## Next steps (the new session)
1. `git merge origin/main`.
2. **Rerun the vertical comparison on the stacked trays (user correction, 06:20).** The rig is separate trays stacked one above the other, not one tray (see the top of [demo-rig.md](demo-rig.md)), so the VERTICAL.md runs on `inserts:5mm` cover only one level.
   - Repeat `sweep.py vertical` on **`inserts:5mm,2mm`** with pasta + rice + quinoa: 0 / 45 / 90° at equal peak acceleration, 3 friction sets.
   - Add a `--design` override to the preset if needed.
   - Report it per level: does each class end on its own tray? Does up-and-down shaking make grains bounce back up, or jam between the trays (`between`)?
   - Add a section to `VERTICAL.md` and open a PR. This is what the demo and the bambu viewer show, so do it first.
3. **Check the optimizer's winners independently.** When `sim/opt/leaderboard.md` / `winners.json` land on `main` (see [design-optimizer.md](design-optimizer.md)):
   - Rerun the top 3 and the stacked `inserts:5mm,2mm` baseline with more seeds (6 × 3 friction sets) and the heavy load.
   - Use the stiffer contacts from VERTICAL.md for any candidate with a gate clearance under ~0.3 mm and a vertical stroke component.
   - Does the ranking hold? Write it up in `sim/opt/VERIFY.md` and open a PR.
   - The optimizer's own runs are the screening; this is the second opinion the honesty rules ask for.
4. **Until winners exist:** if the optimizer session hasn't used VERTICAL.md's "For the optimizer" notes, add a small helper in a **new** file (e.g. `sim/contact_rule.py`) that picks (dt, timeconst) from a design's tightest clearance and the stroke's vertical component, and say so in [README.md](README.md). Don't edit `optimize.py`; that session owns it.
5. **Then be the extra hand** for whichever session is blocked: optimizer, or bambu (the up-and-down demo replay; the command is in VERTICAL.md's "Reproduce").

## Rules
- **Cores:** 24 in total, and the optimizer runs 16 workers. Use **`--workers 8` or fewer** while `optimize.py` is running (`ps aux | grep optimize.py` in WSL).
- Don't recreate `~/venvs/sieve`. Add packages with `uv pip install --python ~/venvs/sieve/bin/python ...` and say so in the PR.
- Don't touch Smart App Control (it's one-way). Ask the user first.
- The sim models the stacked trays, the grains and the shaking, not the DeWalt tool.
- Push to `physics-bench` and open PRs; the main session merges them.

## Status (physics session, 2026-10-25 10:15)
- **Steps 1, 2 and 4 are done** (PR #6): the stacked-rig result is in VERTICAL.md, and the contact rule is `sim/contact_rule.py`.
- **Step 3 is done for the 07:14 winners**, in [`sim/opt/VERIFY.md`](../../sim/opt/VERIFY.md).
  - At the study load the ranking changes, but within noise on the mean: the gated tower comes first on robust, because it varies less.
  - Under the heavy load the optimizer's order holds.
  - The firmware plinko's score leans on soft contacts.
  - `contact_rule.py` picks too soft a setting for the stacked rig.
- **The run was stopped at 200 of 234** because the laptop ran low on memory (2.3 of 31 GB free). The winners are complete; 34 demo-rig runs are missing.
- **Not verified yet: the 09:39 winners** (P-ae394887, P-b192da7c, G-a1ecf9bb). When memory allows, and somebody asks for it:
  - `python verify.py --study demo --top 3 --seeds 6 --heavy 2 --workers 8`: about 2 h at 8 workers; the cached demo-rig runs are reused.
  - Or add `--variants normal`: about 40 min.
- **Also open:** rerun the contact-rule grid with `inserts:5mm,2mm` added.

## Status (physics session, 2026-10-25 11:35)
- **Grains from the team's pantry photo** (asked for by the user): six new kinds in `sim/grains.py`, written up in [`sim/GRAINS.md`](../../sim/GRAINS.md).
  - The kinds are `white_rice` (the photo's white rice: 7.2 × 2.1 × 1.7 mm, 21 mg), `brown_rice`, `black_rice` (short and medium pigmented, black and red), `wild_rice` (one capsule), `chia` and `couscous`.
  - rice, quinoa, chickpea and pasta are frozen and byte-identical, so the optimizer's leaderboard stands.
  - Record the bench's white rice as `white_rice`. Rows of `rice` or `pasta` in `bench/grain_dims.csv` would replace the frozen kinds for every run (GRAINS.md, Suggested changes 5).
- **Bugs:** `sim/insects.py` already models them. [`sim/INSECT_AUDIT.md`](../../sim/INSECT_AUDIT.md) compares it with real Malaise samples and ranks six proposals. None are applied; waiting on the user.

## Status (physics session, 2026-10-25 12:50, relaunched at 12:25 for PLAN.md)
- **Step 1 done (PR #19, merged):** the real Malaise mix. New kinds `insect_malaise` (real shares) and `insect_malaise_lt2` / `_2to6` / `_gt6` (stratified), presets `insects.MALAISE_MIX`, `MALAISE_MIX_STRATIFIED` and `MALAISE_SHARES`. They work in `--mix` and `--clump`. Run them with `--dt 0.000125 --timeconst 0.00025`: at 0.5 ms the smallest specimens pass through the trays. Details are in `sim/INSECT_AUDIT.md` under "Applied at 12:35".
- **Step 2 cut short (PR, 12:58):** `sim/opt/VERIFY_SEESAW.md` has 8 of the demo rig's 18 runs. Claude Code stopped the batch at 12:53 because Windows had 214 MB free of 32 GB. The demo rig on ±10° scores robust 0.36: 40% of the quinoa and 20% of the rice are still on 5 mm after 8 s, and 17% of the rice slips through 2 mm. Don't rerun it until memory allows; the command is in its Reproduce section, and the 8 cached runs are reused.
- **The script:** `sim/verify_seesaw.py` reruns the demo rig (`inserts:5mm,2mm,pitch=85`) and the demo winners P-ae394887 / P-b192da7c (each one box) on the alternating seesaw, ±10°, 2 s, for 8 s, at the optimizer's contacts. It writes `sim/opt/VERIFY_SEESAW.md`.
  - The gated winner is skipped: the optimizer's round 7 found gated can't sort on a symmetric seesaw.
  - The optimizer's seesaw winners (`winners_seesaw.json`) are picked up when they land. At 12:45 the optimizer wasn't running: its out dir had a STOP file and `optimize.py` had uncommitted changes.
  - Cost: about 3 min per 8 s demo-rig run, and about 4x that for a one-box plinko (every rod rides the moving hinge), so the plinkos get 2 seeds × 3 friction sets.
