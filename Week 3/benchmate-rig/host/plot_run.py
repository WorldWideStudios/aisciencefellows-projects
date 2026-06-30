"""
plot_run.py — turn a titration/viability run into a slide-ready blue→pink curve PNG.

    python plot_run.py                 # plots the most recent titration run
    python plot_run.py path/to/run.csv # plots a specific run

Needs matplotlib:  pip install matplotlib
"""
import csv, glob, os, sys

base = "data/rig"
try:
    from benchmate_titrator import DATA_DIR
    base = str(DATA_DIR)
except Exception:
    pass

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    cands = sorted(glob.glob(os.path.join(base, "titration-*.csv"))) or sorted(glob.glob(os.path.join(base, "*.csv")))
    if not cands:
        sys.exit("No run CSV found. Run `python benchmate_titrator.py demo` first.")
    path = cands[-1]

rows = list(csv.DictReader(open(path)))
x = [float(r.get("volume_ul", r.get("t_s", i))) for i, r in enumerate(rows)]
ycol = "rb" if "rb" in rows[0] else ("index" if "index" in rows[0] else list(rows[0])[-1])
y = [float(r[ycol]) for r in rows]

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    import numpy as np
except Exception:
    lo, hi = min(y), max(y) or 1
    blocks = "_.-=+*#@"
    spark = "".join(blocks[min(7, int((v - lo) / ((hi - lo) or 1) * 7))] for v in y)
    print("blue->pink (red/blue ratio) over the run:")
    print(spark)
    print("start %.2f  ->  end %.2f   (%d reads)" % (y[0], y[-1], len(y)))
    sys.exit(0)

xa, ya = np.array(x), np.array(y)
t = (ya - ya.min()) / ((ya.max() - ya.min()) or 1)
pts = np.array([xa, ya]).T.reshape(-1, 1, 2)
segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("bp", ["#3f73a8", "#9a4f93", "#d23f86"])
lc = LineCollection(segs, cmap=cmap, linewidth=3)
lc.set_array(t[:-1])

fig, ax = plt.subplots(figsize=(7, 4))
ax.add_collection(lc)
ax.scatter(xa, ya, c=t, cmap=cmap, s=28, zorder=3, edgecolor="white", linewidth=0.6)
ax.set_xlim(xa.min() - 5, xa.max() + 5)
ax.set_ylim(ya.min() - 0.1, ya.max() + 0.1)
ax.set_xlabel("titrant dispensed (uL)")
ax.set_ylabel("red / blue ratio  (blue -> pink)")
ax.set_title("Closed-loop run: blue -> pink")
ax.grid(True, color="#e2e8f0", linewidth=0.6)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
out = os.path.splitext(path)[0] + ".png"
fig.tight_layout(); fig.savefig(out, dpi=160)
print("saved", out)
