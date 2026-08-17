#!/usr/bin/env python3
"""
composition.py — call-composition bars for runs too long to draw one square per call.

  python3 composition.py --png -o fig.svg "Run 0=baseline:run_0/session_0.jsonl" ...
  python3 composition.py -o fig.svg "n = 8 papers::" "Run 0:s0a.jsonl" "n = 200::" "Run 0:s0.jsonl"

strip_one.py draws one square per call, which stops being readable somewhere north
of ~40 calls. This renders the same sequence as a proportional bar: consecutive
calls of the same bin collapse into one segment, and every run is normalized to
the SAME width. The comparison is therefore SHAPE — what kind of call, in what
order — not length. The total call count prints at the right end.

Two bins only, so the figure says nothing about which tool was used:
  READ   a call that returned document text   (pc_search/pc_read/pc_analyze/local_read)
  OTHER  everything else                      (setup, local_work)

An empty path draws a group heading row instead of a bar, for stacking two
conditions in one figure ("n = 8 papers::" with no path after the colon).

The dark underline marks the portion of a READ segment whose result carried a
line address (strip_one.trust_for() == 3). That is the channel the figure is
built to carry: how precisely a downstream claim could point at its origin.

A locator coming back is not the same as a claim being checked against it.

Every value comes from strip_one.sequence(), which reads the session .jsonl.
Nothing here is model-generated; re-running on the same log is byte-identical.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strip_one import sequence

W, ROW_H, BAR_H, LEFT, PAD_R, TOP = 640, 44, 22, 104, 62, 8
INK, MUTED = "#1A1D19", "#5E6B63"
READ_KINDS = {"pc_search", "pc_read", "pc_analyze", "local_read"}
READ_FILL, OTHER_FILL = "#4C8DD9", "#D8D4CC"

def rle(seq):
    segs = []
    for kind, _failed, trust in seq:
        b = "read" if kind in READ_KINDS else "other"
        if segs and segs[-1][0] == b:
            segs[-1][1] += 1; segs[-1][2] += (trust == 3)
        else:
            segs.append([b, 1, int(trust == 3)])
    return segs

def build(runs, out, legend=True, png=False, scale=3):
    data = [(l, s, (None if p is None else (sequence(p) if isinstance(p, str) else p)))
            for l, s, p in runs]
    lh = 34 if legend else 0
    H = TOP + len(data)*ROW_H + lh + 4
    o = [f'<svg viewBox="0 0 {LEFT+W+PAD_R} {H}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="system-ui,sans-serif">',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for i,(lab,sub,seq) in enumerate(data):
        y=TOP+i*ROW_H
        if seq is None:                      # group heading row
            o.append(f'<text x="4" y="{y+16}" font-size="12" font-weight="600" '
                     f'fill="{MUTED}" letter-spacing="0.6">{lab}</text>')
            if sub:
                o.append(f'<line x1="{LEFT}" y1="{y+11}" x2="{LEFT+W}" y2="{y+11}" '
                         f'stroke="#E2E2E0" stroke-width="1"/>')
            continue
        n=len(seq)
        o.append(f'<text x="4" y="{y+10}" font-size="12" font-weight="600" fill="{INK}">{lab}</text>')
        if sub: o.append(f'<text x="4" y="{y+21}" font-size="9" fill="#7C847D">{sub}</text>')
        x=LEFT
        for b,cnt,t3 in rle(seq):
            w=W*cnt/n
            o.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w-0.6,0.6):.1f}" height="{BAR_H}" '
                     f'fill="{READ_FILL if b=="read" else OTHER_FILL}"/>')
            if t3:
                uw=max(w*t3/cnt-0.6,0.6)
                o.append(f'<rect x="{x:.1f}" y="{y+BAR_H-7}" width="{uw:.1f}" height="1" fill="#FFFFFF"/>')
                o.append(f'<rect x="{x:.1f}" y="{y+BAR_H-6}" width="{uw:.1f}" height="6" fill="{INK}"/>')
            x+=w
        na=sum(1 for _,_,t in seq if t==3)
        o.append(f'<text x="{LEFT+W+8}" y="{y+15}" font-size="11" fill="{MUTED}">{n}</text>')
    if legend:
        ly=TOP+len(data)*ROW_H+12; lx=4
        for fill,name in ((READ_FILL,'read'),(OTHER_FILL,'other')):
            o.append(f'<rect x="{lx}" y="{ly}" width="13" height="13" rx="2" fill="{fill}"/>')
            o.append(f'<text x="{lx+18}" y="{ly+11}" font-size="11" fill="{MUTED}">{name}</text>')
            lx+=18+len(name)*6.2+26
        o.append(f'<rect x="{lx}" y="{ly}" width="13" height="13" rx="2" fill="{OTHER_FILL}"/>')
        o.append(f'<rect x="{lx}" y="{ly+6}" width="13" height="1" fill="#FFFFFF"/>')
        o.append(f'<rect x="{lx}" y="{ly+7}" width="13" height="6" fill="{INK}"/>')
        o.append(f'<text x="{lx+18}" y="{ly+11}" font-size="11" fill="{MUTED}">line address returned</text>')
    o.append('</svg>')
    svg="\n".join(o); open(out,'w').write(svg)
    for l,_,sq in data:
        if sq is not None:
            print(f"  {l:<16}{len(sq):>4} calls  {sum(1 for _,_,t in sq if t==3):>4} line-addressed")
    if png:
        import cairosvg
        p=out[:-4]+'.png'
        cairosvg.svg2png(bytestring=svg.encode(), write_to=p, scale=scale, background_color='white')
        print(f"{p}  (scale {scale}x)")

def parse(spec):
    """'Run 0=baseline:path.jsonl' | 'Run 0:path.jsonl' | 'HEADING::' | 'path.jsonl'"""
    if ':' in spec and not os.path.exists(spec):
        head, path = spec.rsplit(':', 1)
        lab, _, sub = head.partition('=')
        return lab, sub, (path or None)          # empty path -> group heading row
    return os.path.basename(spec).replace('.jsonl',''), '', spec

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs',nargs='+'); ap.add_argument('-o','--out',default='composition.svg')
    ap.add_argument('--no-legend',action='store_true'); ap.add_argument('--png',action='store_true')
    ap.add_argument('--scale',type=float,default=3)
    a=ap.parse_args()
    build([parse(s) for s in a.runs], a.out, not a.no_legend, a.png, a.scale)
