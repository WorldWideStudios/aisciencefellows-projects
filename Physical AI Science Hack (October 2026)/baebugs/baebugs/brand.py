"""baebugs logo: a cute beetle whose shell is a heart ("bae" bug), plus the wordmark, as pure SVG paths.

  python -m baebugs.brand --font path/to/bricolage-grotesque-latin-800-normal.woff  -> assets/brand/*
The wordmark is converted to outlines (Bricolage Grotesque, SIL Open Font License) so the SVGs need no font.
"""
from __future__ import annotations

import argparse
from pathlib import Path

INK = "#1c2747"        # navy head, legs, spots
SHELL = "#f2545b"      # heart shell
SHELL_DARK = "#d63c46"
CHEEK = "#ff9aa2"


def mark(ink=INK, line=None):
    line = line or ink                      # legs/antennae (light on dark backgrounds)
    legs = "".join(
        f'<path d="M{x1} {y1} Q{qx} {qy} {x2} {y2}" fill="none" stroke="{line}" stroke-width="7" stroke-linecap="round"/>'
        for (x1, y1, qx, qy, x2, y2) in [(70, 100, 46, 92, 34, 78), (64, 124, 40, 124, 26, 120), (72, 148, 50, 160, 40, 174),
                                         (130, 100, 154, 92, 166, 78), (136, 124, 160, 124, 174, 120), (128, 148, 150, 160, 160, 174)])
    antennae = (f'<path d="M90 42 Q80 18 62 16" fill="none" stroke="{line}" stroke-width="5" stroke-linecap="round"/>'
                f'<path d="M110 42 Q120 18 138 16" fill="none" stroke="{line}" stroke-width="5" stroke-linecap="round"/>'
                f'<circle cx="60" cy="16" r="6" fill="{SHELL}"/><circle cx="140" cy="16" r="6" fill="{SHELL}"/>')
    heart = "M100 186 C46 152 28 112 48 88 C64 69 90 72 100 92 C110 72 136 69 152 88 C172 112 154 152 100 186 Z"
    shell = (f'<path d="{heart}" fill="{SHELL}"/>'
             f'<path d="{heart}" fill="none" stroke="{SHELL_DARK}" stroke-width="3"/>'
             f'<path d="M100 96 L100 178" stroke="{SHELL_DARK}" stroke-width="3" stroke-linecap="round"/>'
             '<ellipse cx="68" cy="104" rx="12" ry="7" transform="rotate(-35 68 104)" fill="#ffffff" opacity=".35"/>'
             f'<circle cx="74" cy="122" r="7" fill="{ink}"/><circle cx="126" cy="122" r="7" fill="{ink}"/>'
             f'<circle cx="86" cy="152" r="5.5" fill="{ink}"/><circle cx="114" cy="152" r="5.5" fill="{ink}"/>')
    ring = "" if line == ink else f' stroke="{line}" stroke-width="3"'
    head = (f'<circle cx="100" cy="62" r="27" fill="{ink}"{ring}/>'
            '<circle cx="89" cy="58" r="8" fill="#ffffff"/><circle cx="111" cy="58" r="8" fill="#ffffff"/>'
            f'<circle cx="90.5" cy="59.5" r="4.2" fill="{ink}"/><circle cx="112.5" cy="59.5" r="4.2" fill="{ink}"/>'
            '<circle cx="92" cy="57.5" r="1.5" fill="#ffffff"/><circle cx="114" cy="57.5" r="1.5" fill="#ffffff"/>'
            f'<circle cx="80" cy="70" r="4" fill="{CHEEK}" opacity=".9"/><circle cx="120" cy="70" r="4" fill="{CHEEK}" opacity=".9"/>'
            '<path d="M93 72 Q100 78 107 72" fill="none" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round"/>')
    return legs + antennae + shell + head


def wordmark_path(font_file, text="baebugs", size=120):
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    f = TTFont(font_file)
    gs, cmap, upm = f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm
    s = size / upm
    x, parts = 0.0, []
    for ch in text:
        gname = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[gname].draw(TransformPen(pen, (s, 0, 0, -s, x, 0)))
        parts.append(pen.getCommands())
        x += gs[gname].width * s - size * 0.012
    asc = f["hhea"].ascent * s
    return " ".join(parts), x, asc


def svg(inner, w, h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="baebugs">{inner}</svg>\n'


def build(font, out="assets/brand"):
    o = Path(out); o.mkdir(parents=True, exist_ok=True)
    files = {}
    files["baebugs_mark.svg"] = svg(f"<title>baebugs</title>{mark()}", 200, 200)
    d, wlen, asc = wordmark_path(font)
    files["baebugs_mark_dark.svg"] = svg(f"<title>baebugs</title>{mark(INK, '#cfd6f2')}", 200, 200)
    for name, line, word in (("baebugs_logo.svg", INK, INK), ("baebugs_logo_dark.svg", "#cfd6f2", "#f4f1fb")):
        inner = (f"<title>baebugs</title><g>{mark(INK, line)}</g>"
                 f'<g transform="translate(222 {100 + asc * 0.36:.1f})"><path d="{d}" fill="{word}"/></g>')
        files[name] = svg(inner, 222 + wlen + 16, 200)
    for k, v in files.items():
        (o / k).write_text(v)
    return files


def render_png(out="assets/brand"):
    """PNG renders for slides/social (needs Playwright)."""
    from playwright.sync_api import sync_playwright
    o = Path(out).resolve()
    jobs = [("baebugs_mark.svg", "baebugs_mark_512.png", 512, None), ("baebugs_logo.svg", "baebugs_logo_light.png", 1200, "#ffffff"),
            ("baebugs_logo_dark.svg", "baebugs_logo_dark.png", 1200, "#141a2e"), ("baebugs_mark.svg", "favicon_64.png", 64, None)]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for src, dst, w, bg in jobs:
            s = (o / src).read_text()
            vb = [float(v) for v in s.split('viewBox="')[1].split('"')[0].split()]
            h = round(w * vb[3] / vb[2])
            pg = b.new_page(viewport={"width": w, "height": h})
            style = f'style="width:{w}px;height:{h}px;display:block" '
            sized = s.replace("<svg ", "<svg " + style, 1)
            pg.set_content('<html><body style="margin:0;background:' + (bg or "transparent") + '">' + sized + "</body></html>")
            pg.screenshot(path=str(o / dst), omit_background=bg is None)
        b.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--font", required=True); ap.add_argument("--png", action="store_true")
    a = ap.parse_args()
    build(a.font)
    if a.png:
        render_png()
