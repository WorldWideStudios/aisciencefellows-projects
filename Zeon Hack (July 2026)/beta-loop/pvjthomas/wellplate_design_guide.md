# Wellplate design guide — rules and algorithms

Reference for placing samples, controls, and replicates on rectangular microtiter plates (96-, 384-, 1536-well). Layout generation in this repo lives in [`plates.py`](plates.py); PNG rendering in [`ml/analysis/plate_viz.py`](../ml/analysis/plate_viz.py) must never change well positions.

Project-specific enforced rules: [`.cursor/rules/plate-layout.mdc`](../.cursor/rules/plate-layout.mdc).

---

## 1. Problem setup

Given an **m × n** plate (e.g. 8 × 12 for 96-well) and **k** occupied wells (samples, controls, replicates), choose well coordinates to maximize spatial separation while satisfying biological and experimental constraints.

**Notation**

| Symbol | Meaning |
|--------|---------|
| `(r, c)` | 0-based row/column index (rows A–H → 0–7, cols 1–12 → 0–11) |
| `d(i, j)` | Distance between wells *i* and *j* under the chosen metric |
| `k` | Total number of wells to occupy |
| `R` | Replicates per biological sample (often 3) |

**Standard plate sizes**

| Format | Rows × cols | Interior-only block (no edge wells) |
|--------|-------------|-------------------------------------|
| 96-well | 8 × 12 | B–G × 2–11 → 6 × 10 = 60 wells |
| 384-well | 16 × 24 | 14 × 22 |
| 1536-well | 32 × 48 | 30 × 46 |

For a regular grid, all pairwise distances are fixed and can be **precomputed once** into a distance matrix `D[i,j]`, enabling fast scoring without simulation.

---

## 2. Distance metrics

Choose the metric that matches how edge effects propagate on the plate:

| Metric | Formula | When to use |
|--------|---------|-------------|
| **Euclidean** | `√((r₁−r₂)² + (c₁−c₂)²)` | General-purpose; smooth isotropic spreading |
| **Manhattan** | `|r₁−r₂| + |c₁−c₂|` | Grid-aligned movement; row/column banding |
| **Chebyshev** | `max(|r₁−r₂|, |c₁−c₂|)` | Effects spread in all diagonal directions equally (king's-move on chessboard) |

On a unit-spaced grid, Chebyshev distance 1 means orthogonally or diagonally adjacent wells share an edge or corner.

---

## 3. Case 1 — Maximize separation among all occupied wells

Place **k** samples with no replicate structure. Goal: spread wells as evenly as possible.

### 3.1 Objectives

**Maximin (most common)**

```
max  min_{i≠j} d(x_i, x_j)
```

Maximizes the *minimum* pairwise distance. Produces very even layouts; no pair is squeezed together.

**Sum of pairwise distances**

```
max  Σ_{i<j} d(x_i, x_j)
```

Can improve average spacing but may sacrifice the worst pair — one close neighbor is acceptable if many others are far apart.

### 3.2 Greedy farthest-point sampling (Gonzalez's algorithm)

Often within a few percent of optimal for rectangular grids. No simulation required.

```
Algorithm: Farthest-Point Sampling
Input:  empty plate, k samples to place
Output: set S of k well coordinates

1. Pick an initial well s₁ (center or a corner of the allowed region).
2. For t = 2 … k:
     For each empty well w:
       dist(w) ← min_{s ∈ S} d(w, s)    // distance to nearest occupied well
     s_t ← argmax_w dist(w)              // farthest from all occupied wells
     S ← S ∪ {s_t}
3. Return S
```

Also called **farthest-first traversal**. Runs in O(k · m · n) per step; trivial for 96/384-well plates.

**Initial well choice:** center of the allowed region for symmetric layouts; a corner if edge wells are forbidden and you want to fill from the interior outward.

### 3.3 Relation to this repo

| Mode | Strategy |
|------|----------|
| `spaced_interior` | Hand-crafted checkerboard on interior block — every occupied sample well has no orthogonal neighbor (Chebyshev ≥ 2 on unit grid) |
| `column_strip` | Column-band pattern with enforced horizontal separation (`validate_sample_x_separation`) |

Both modes are **deterministic patterns** that approximate maximin on the 96-well interior rather than running farthest-point at generation time.

---

## 4. Case 2 — Replicates must also be separated

Each biological sample has **R** replicates (typically R = 3). Two scales of separation:

1. **Global:** all occupied wells should be spread out.
2. **Within-sample:** replicates of the *same* compound should be *especially* far apart.

### 4.1 Weighted objective

```
Score = α · min_{i,j} d(i,j)  +  β · Σ_{(i,j) replicate pairs} d(i,j)
```

with **β > α**. Replicate pairs contribute more to the score, so the optimizer pushes them apart first.

Equivalent formulation: assign each replicate pair a larger repulsive weight in a force-based model (see §8).

### 4.2 Two-phase assignment

When there are **G** sample groups × **R** replicates = **G·R** sample wells:

1. Use farthest-point sampling to choose **G·R** well locations (maximin layout).
2. **Assign** replicate groups to those locations to maximize replicate-pair distances (assignment problem or greedy matching).

Step 2 alone is insufficient if the well set was chosen without replicate structure — always optimize *placement* and *assignment* together or iterate.

### 4.3 Relation to this repo

Triplicate controls are placed at columns **3, 7, 11** on rows B, D, F — maximum horizontal separation within the interior (`SPACED_CONTROL_COLS`). Sample replicates in `column_strip` mode use disjoint column bands (2/4/6/8/10 vs 5/9 vs 3/7) so replicates of different compounds rarely share a row.

---

## 5. Case 3 — Hard constraints (row, column, quadrant, edge)

Many screens add **constraints** that must be satisfied exactly, not merely optimized:

| Constraint | Rationale |
|------------|-----------|
| Replicates not in same row | Row-wise liquid handling / edge evaporation |
| Replicates not in same column | Column-wise pipetting bias |
| Different quadrants | Spatial batch effects |
| No edge wells | Rim evaporation, temperature gradients |
| Interior block only | B–G × 2–11 on 96-well (see `validate_interior_layout`) |

With constraints, the problem becomes:

```
maximize spacing  subject to  constraint set C
```

Feasibility must be checked before optimization. If constraints over-constrain (e.g. 3 replicates, no shared row *and* no shared column on a small plate), relax constraints or reduce R.

### 5.1 Constraint examples as predicates

```python
def same_row(i, j) -> bool:
    return i.row == j.row

def same_col(i, j) -> bool:
    return i.col == j.col

def same_quadrant(i, j, n_rows, n_cols) -> bool:
    return (i.row < n_rows // 2) == (j.row < n_rows // 2) and \
           (i.col < n_cols // 2) == (j.col < n_cols // 2)

def is_edge(i, n_rows, n_cols) -> bool:
    return i.row in (0, n_rows - 1) or i.col in (0, n_cols - 1)
```

For replicate pair `(i, j)` of the same sample: reject if `same_row(i,j) or same_col(i,j)` (and optionally `same_quadrant`).

### 5.2 Relation to this repo

Enforced in `plates.py`:

- **No edge wells** for `spaced_interior` and `column_strip` (`EDGE_ROWS`, `EDGE_COLS`).
- **No horizontally adjacent samples on the same row** (`validate_sample_x_separation`).
- **Controls at spaced columns** 3, 7, 11 — one triplicate group per row band.

---

## 6. Graph formulation

Model the plate as a graph **G = (V, E)**:

- **V** — one vertex per well.
- **E** — edge weights `w(i,j) = d(i,j)` (from precomputed distance matrix).

Assign samples (and replicate groups) to vertices while maximizing edge weights between **related** vertices (same sample → high weight / hard constraint; different samples → dispersion).

This connects to classical problems:

| Problem | Role |
|---------|------|
| **Graph labeling** | Assign labels (sample IDs) to vertices |
| **Quadratic assignment (QAP)** | Assign facilities to locations minimizing flow × distance |
| **Maximum dispersion (MDP)** | Choose k vertices maximizing sum of pairwise distances |
| **p-dispersion** | Choose k vertices maximizing minimum pairwise distance (maximin) |

For 96- and 384-well plates with modest k, exact methods (ILP, branch-and-bound on precomputed D) are often feasible unless constraint count is very high.

---

## 7. Optimization methods

Simulation is **not required**. Several deterministic or heuristic methods work well:

| Method | Pros | Cons |
|--------|------|------|
| **Greedy farthest-point** | Fast, simple, near-optimal for unconstrained maximin | Ignores replicate structure and hard constraints |
| **Integer linear programming (ILP)** | Exact or near-exact with linearized objectives | Formulation effort; solver needed |
| **Mixed-integer quadratic programming (MIQP)** | Natural for Σ d² or weighted sums | Heavier than ILP |
| **Simulated annealing** | Escapes local optima; flexible constraints | Tuning temperature schedule |
| **Tabu search** | Good for swap-based neighborhoods | Parameter tuning |
| **Genetic algorithms** | Handles messy constraint sets | Overkill for 96-well |

**When exact optimization is feasible:** k ≤ 60 interior wells on 96-well, distance matrix precomputed, constraints linear — ILP/p-dispersion solvers often finish in seconds.

**When heuristics suffice:** farthest-point init + local search typically reaches layouts indistinguishable from optimal in the lab.

---

## 8. Practical hybrid algorithm

Recommended pipeline for constrained multi-replicate layouts:

```
Phase 1 — Initial placement
  Run farthest-point sampling on the feasible well set
  (respecting edge/quadrant exclusions).
  → set of k well coordinates

Phase 2 — Replicate assignment
  Assign R wells to each of G sample groups on those coordinates.
  Greedy: assign the replicate group with largest internal spread first;
  or solve assignment to maximize β-weighted replicate distances.

Phase 3 — Local improvement
  Repeat until no improvement:
    Propose swap of two occupied wells (or swap assignment between groups).
    Accept if Score increases (§4.1) and all hard constraints (§5) hold.

Phase 4 — Simulated annealing (optional)
  Allow occasional uphill moves to escape local optima.
  Cool from T₀ to T_min over fixed iterations.
  Typical neighborhood: swap two sample wells or exchange one replicate.
```

**Pseudocode — local swap improvement**

```python
def improve_layout(wells, score_fn, feasible_fn, max_iter=10_000):
    best = wells
    best_score = score_fn(best)
    for _ in range(max_iter):
        candidate = propose_swap(best)          # swap two positions or assignments
        if not feasible_fn(candidate):
            continue
        s = score_fn(candidate)
        if s > best_score:
            best, best_score = candidate, s
    return best
```

---

## 9. Electrostatic (physics) analogy

Treat each occupied well as a **point charge**. Pairwise repulsive energy:

```
E = Σ_{i<j}  w_ij / d(i,j)^p
```

- **w_ij = 1** for unrelated pairs (different samples).
- **w_ij = β/α > 1** for replicate pairs of the same sample.

Minimizing **E** spreads all wells apart; larger replicate weights push triplicates farther from each other. This is equivalent to force-directed layout and is widely used in experimental design software.

**Connection to objectives:**

| p | Limiting behavior |
|---|-------------------|
| p → ∞ | Approaches hard exclusion (infinite penalty at d = 0) |
| p = 1 | Related to sum of inverse distances |
| Large β on replicate pairs | Approximates §4.1 weighted sum |

Gradient descent or simulated annealing on **E** is a smooth alternative to discrete swap search.

---

## 10. Precomputation for standard grids

Because well positions are fixed on a rectangular grid:

1. **Enumerate** all wells (or all interior wells).
2. **Build** `D ∈ ℝ^{N×N}` once for each metric (Euclidean, Manhattan, Chebyshev).
3. **Index** wells by integer 0 … N−1; store `(row, col)` lookup tables.
4. **Score** any layout by summing `D[i,j]` over selected pairs — O(k²) per evaluation.

For branch-and-bound maximin: maintain running minimum pairwise distance as wells are added; prune branches that cannot beat the incumbent.

```python
def precompute_distances(rows, cols, metric="chebyshev"):
    import numpy as np
    n = rows * cols
    D = np.zeros((n, n))
    for i in range(n):
        r1, c1 = divmod(i, cols)
        for j in range(i + 1, n):
            r2, c2 = divmod(j, cols)
            if metric == "euclidean":
                d = ((r1 - r2) ** 2 + (c1 - c2) ** 2) ** 0.5
            elif metric == "manhattan":
                d = abs(r1 - r2) + abs(c1 - c2)
            else:  # chebyshev
                d = max(abs(r1 - r2), abs(c1 - c2))
            D[i, j] = D[j, i] = d
    return D
```

---

## 11. Decision guide — which approach to use

```
Start
  │
  ├─ Only k samples, no replicates, no extra constraints?
  │     → Farthest-point sampling (§3.2); maximin objective
  │
  ├─ Replicates (R > 1)?
  │     → Weighted objective (§4.1) or electrostatic (§9)
  │     → Hybrid: farthest-point init + assignment + local swaps (§8)
  │
  ├─ Hard row/column/quadrant/edge rules?
  │     → Filter feasible wells first (§5)
  │     → Then optimize on feasible set; validate with predicates
  │
  └─ Need proven optimum or audit trail?
        → ILP / p-dispersion on precomputed D (§6, §7)
        Else heuristics are sufficient for 96/384-well lab use
```

---

## 12. This repository — layout modes summary

| Mode | Case | Algorithm class | Key validators |
|------|------|-----------------|----------------|
| `compact` | Packed | Sequential fill | None (legacy) |
| `spaced_interior` | 1 + 3 | Checkerboard pattern ≈ maximin | `validate_interior_layout` |
| `column_strip` | 1 + 2 + 3 | Column bands + x-separation | `validate_interior_layout`, `validate_sample_x_separation` |

**Compound placement** (independent of geometry): positive control compound (`T19860`) must not also appear in the discovery sample list — see `COMPOUND_PLACEMENT_RULES` in `plates.py`.

**When adding a new layout mode:**

1. Document which case(s) and objective it targets in this guide.
2. Add entries to `LAYOUT_RULES` in `plates.py`.
3. Call `validate_interior_layout` (and other validators) if interior-only.
4. Update build scripts and `runs/<screen>/<version>/selection_rationale.md`.
5. Do **not** change concentrations when only changing layout.

---

## 13. References (literature keywords)

- **Gonzalez's algorithm** — farthest-first traversal for k-center / maximin dispersion
- **Maximum dispersion problem (MDP)** — maximize Σ d(i,j) over chosen pairs
- **p-dispersion problem** — maximize min d(i,j) (maximin)
- **Quadratic assignment problem (QAP)** — facility layout with flow matrices
- **Simulated annealing / tabu search** — metaheuristics for constrained plate design
- **Space-filling designs** — Latin hypercube and maximin distance designs (continuous analogs)

For standard 96-, 384-, and 1536-well plates, precomputed distance matrices plus farthest-point initialization and local swap improvement typically yield layouts that are effectively optimal for laboratory purposes within seconds.
