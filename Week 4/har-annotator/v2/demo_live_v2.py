#!/usr/bin/env python
"""demo_live_v2.py -- the v2 live demo of the HAR pipeline (superset of v1).

Same fast, offline, glass-box demo as demo_live.py (the shipped v1), plus the
two v2 build-outs. Runs in <1 second from precomputed evidence (no network, no
long compute), so it's safe to run in front of an audience.

The three v1 moves (unchanged from demo_live.py):
    python demo_live_v2.py                     # funnel + top 10 ranked
    python demo_live_v2.py --gene ZSWIM6       # axis decomposition for one hit
    python demo_live_v2.py --weight motif=0.30 # RE-RANK live with a changed weight

The two v2 moves:
    python demo_live_v2.py --discovery         # v2.0: drop the disease gate, show new biology
    python demo_live_v2.py --neglect 0.25      # v1.1: reward understudied target genes

--weight is the original money shot: change what you care about, watch the
ranking reshuffle instantly. --discovery opens the aperture (363 -> 577, 214 new
elements near non-disease genes, no disease-gene requirement); --neglect re-ranks
toward under-studied genes. That is the whole "glass box" thesis, made live.

v1 is preserved as demo_live.py (disease-anchored, 3 moves) for reference. This
v2 script is a strict superset and reads the same precomputed parquets.

Add --no-color to strip ANSI codes (for logs / projectors that mangle them).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from har_annotator.score import compute_scores, WEIGHTS, COMPONENTS

RANKED = "har_shortlist_ranked.parquet"
DISCOVERY = "har_shortlist_discovery.parquet"
NEGLECT = "har_shortlist_neglect.parquet"
C = dict(ink="\033[38;5;238m", acc="\033[38;5;168m", grn="\033[38;5;29m",
         mut="\033[38;5;66m", bold="\033[1m", dim="\033[2m", off="\033[0m",
         up="\033[38;5;29m", dn="\033[38;5;168m")

def no_color():
    for k in C:
        C[k] = ""

def load():
    df = pd.read_parquet(RANKED)
    # strip the precomputed rank/score/contrib columns so compute_scores can
    # rebuild them cleanly from the raw evidence columns.
    drop = [c for c in df.columns
            if c == "rank" or c.startswith("score_")
            or c.startswith("contrib_") or c == "total_score"]
    return df.drop(columns=drop)

def funnel():
    print(f"\n{C['bold']}HAR prioritization funnel{C['off']}")
    for label, n in [("All HARs (Cui et al. 2025)", 3257),
                     ("constrained (phyloP)", 2757),
                     ("near a neurodev gene", 1718),
                     ("+ disease-signal overlap  ->  scored", 363)]:
        bar = "#" * max(1, round(n / 3257 * 40))
        print(f"  {C['mut']}{bar:<40}{C['off']} {n:>5}  {label}")

def funnel_discovery():
    print(f"\n{C['bold']}HAR discovery funnel (v2.0 — disease gate dropped){C['off']}")
    for label, n in [("All HARs (Cui et al. 2025)", 3257),
                     ("constrained (phyloP)", 2757),
                     ("near ANY gene (<=1Mb)", 2739),
                     ("+ disease-signal overlap  ->  scored", 577)]:
        bar = "#" * max(1, round(n / 3257 * 40))
        print(f"  {C['mut']}{bar:<40}{C['off']} {n:>5}  {label}")
    print(f"  {C['dim']}363 shared with the disease-anchored run + "
          f"{C['acc']}214 newly surfaced{C['off']}{C['dim']} (all near non-disease genes){C['off']}")

def discovery_table(df, n=12):
    print(f"\n{C['bold']}{'#':>4}  {'HAR':<10}{'gene':<12}{'score':>7}  {'source':<8}{C['off']}")
    for _, r in df.head(n).iterrows():
        new = r["surfaced"] == "new"
        mark = f"{C['acc']}{C['bold']}" if new else ""
        endm = C['off'] if mark else ""
        tag = "NEW" if new else "shared"
        print(f"{mark}{int(r['rank']):>4}  {r['har_id']:<10}{str(r['gene']):<12}"
              f"{r['total_score']:>7.3f}  {tag:<8}{endm}")
    newtop = df[df["surfaced"] == "new"].head(8)
    print(f"\n{C['bold']}Top newly-surfaced elements (discovery-only biology){C['off']}")
    for _, r in newtop.iterrows():
        print(f"  {C['acc']}#{int(r['rank']):<4}{C['off']} {str(r['gene']):<12}"
              f"{C['dim']}{r['har_id']}  score {r['total_score']:.3f}{C['off']}")

def neglect_table(df, n=12, w=0.25):
    print(f"\n{C['bold']}Neglect-aware ranking (v1.1, w={w}) — reward understudied target genes{C['off']}")
    print(f"\n{C['bold']}{'#':>4} {'(was)':>6}  {'HAR':<10}{'gene':<12}{'score':>7}{'papers':>8}{C['off']}")
    for _, r in df.head(n).iterrows():
        shift = int(r["shift"])
        if shift > 0:   mv = f"  {C['up']}^{shift}{C['off']}"
        elif shift < 0: mv = f"  {C['dn']}v{abs(shift)}{C['off']}"
        else:           mv = ""
        few = f"{C['acc']}" if r["pubmed"] <= 40 else ""
        print(f"{int(r['rank_neglect']):>4} {int(r['rank']):>6}  {r['har_id']:<10}"
              f"{str(r['gene']):<12}{r['total_neglect']:>7.3f}"
              f"{few}{int(r['pubmed']):>8}{C['off']}{mv}")
    print(f"\n{C['dim']}^/v = move vs the evidence-only ranking; "
          f"{C['acc']}pink papers{C['off']}{C['dim']} = <=40 PubMed hits (understudied).{C['off']}")

def top_table(df, n=10, highlight=None, prev_rank=None):
    cols = ["rank", "har_id", "gene", "total_score"]
    print(f"\n{C['bold']}{'#':>3}  {'HAR':<10}{'gene':<12}{'score':>7}  {'axes (relative contribution)':<30}{C['off']}")
    for _, r in df.head(n).iterrows():
        contribs = {c: r[f"contrib_{c}"] for c in COMPONENTS}
        top3 = sorted(contribs.items(), key=lambda kv: -kv[1])[:3]
        spark = " ".join(f"{c[:4]}" for c, _ in top3)
        move = ""
        if prev_rank is not None and r["har_id"] in prev_rank.values:
            old = prev_rank[prev_rank == r["har_id"]].index[0] + 1
            d = old - int(r["rank_new"])
            if d > 0:   move = f"  {C['up']}^{d}{C['off']}"
            elif d < 0: move = f"  {C['dn']}v{abs(d)}{C['off']}"
        mark = f"{C['acc']}{C['bold']}" if (highlight and r["gene"] == highlight) else ""
        endm = C['off'] if mark else ""
        print(f"{mark}{int(r['rank_new']):>3}  {r['har_id']:<10}{str(r['gene']):<12}{r['total_score']:>7.3f}  {C['dim']}{spark:<30}{C['off']}{endm}{move}")

def decompose(df, gene):
    row = df[df["gene"].astype(str).str.upper() == gene.upper()]
    if row.empty:
        print(f"  no candidate for gene '{gene}'"); return
    r = row.iloc[0]
    print(f"\n{C['bold']}{r['gene']}  ({r['har_id']}, rank {int(r['rank'])}, total {r['total_score']:.3f}){C['off']}")
    print(f"  {C['dim']}{r['chrom']}:{int(r['start']):,}-{int(r['end']):,}{C['off']}")
    for c in sorted(COMPONENTS, key=lambda c: -r[f"contrib_{c}"]):
        sc, contrib, w = r[f"score_{c}"], r[f"contrib_{c}"], WEIGHTS[c]
        bar = "#" * round(sc * 24)
        flag = f"  {C['acc']}<- near zero: honest weak spot{C['off']}" if sc < 0.05 else ""
        print(f"  {c:<13} score {sc:>5.2f}  x w{w:>5.2f}  = {contrib:>5.3f}  {C['grn']}{bar}{C['off']}{flag}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gene", help="show axis decomposition for this gene")
    ap.add_argument("--weight", action="append", default=[],
                    help="override a weight, e.g. --weight motif=0.30 (repeatable)")
    ap.add_argument("--discovery", action="store_true",
                    help="v2.0: drop the disease-gene gate; show the 577 discovery shortlist")
    ap.add_argument("--neglect", nargs="?", const=0.25, type=float, default=None,
                    help="v1.1: re-rank rewarding understudied genes (optional weight, default 0.25)")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--no-color", action="store_true", help="strip ANSI colors")
    args = ap.parse_args()
    if args.no_color:
        no_color()

    # v2.0 discovery mode — precomputed, offline
    if args.discovery:
        funnel_discovery()
        disc = pd.read_parquet(DISCOVERY)
        discovery_table(disc, args.n if args.n != 10 else 12)
        print(f"\n{C['mut']}same 7 axes, same weights — only the gene gate changed.{C['off']}\n")
        return

    # v1.1 neglect-aware mode — precomputed, offline (re-derive for any w)
    if args.neglect is not None:
        funnel()
        w = args.neglect
        neg = pd.read_parquet(NEGLECT)
        neg["total_neglect"] = (1 - w) * neg["total_score"] + w * neg["score_neglect"]
        neg = neg.sort_values("total_neglect", ascending=False).reset_index(drop=True)
        neg["rank_neglect"] = range(1, len(neg) + 1)
        neg["shift"] = neg["rank"] - neg["rank_neglect"]
        neglect_table(neg, args.n if args.n != 10 else 12, w=w)
        print(f"\n{C['mut']}weights still sum to 1.0: (1-w)*evidence + w*neglect.{C['off']}\n")
        return

    ev = load()
    funnel()

    if args.gene and not args.weight:
        base = compute_scores(ev); base["rank_new"] = range(1, len(base) + 1)
        decompose(base, args.gene); print(); return

    base = compute_scores(ev); base["rank_new"] = range(1, len(base) + 1)

    if not args.weight:
        top_table(base, args.n)
        print(f"\n{C['dim']}default weights: " +
              ", ".join(f"{c} {WEIGHTS[c]}" for c in COMPONENTS) + C['off'])
        print(f"{C['mut']}try:  python demo_live.py --weight motif=0.30{C['off']}\n")
        return

    # RE-RANK with overridden weights
    overrides = {}
    for w in args.weight:
        k, v = w.split("="); overrides[k.strip()] = float(v)
    new = compute_scores(ev, weights=overrides)
    new["rank_new"] = range(1, len(new) + 1)
    prev_rank = base.reset_index(drop=True)["har_id"]

    print(f"\n{C['bold']}Re-ranked with {overrides}{C['off']}  "
          f"{C['dim']}(other weights auto-share the remainder){C['off']}")
    top_table(new, args.n, prev_rank=prev_rank)
    moved = (new.head(args.n)["har_id"].values != base.head(args.n)["har_id"].values).sum()
    print(f"\n{C['acc']}{moved} of the top {args.n} changed position.{C['off']}  "
          f"{C['dim']}Same evidence, different priorities -> different shortlist.{C['off']}\n")

if __name__ == "__main__":
    main()
