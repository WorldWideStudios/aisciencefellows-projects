#!/usr/bin/env python3
"""
strip_one.py — one horizontal strip per run, one square per tool call.

Like strip_figure.py, but you name the inputs instead of relying on a
run_*/session.jsonl glob, and each square carries two channels:

  FILL   = which bin the call belongs to (where the work happened)
  BORDER = how much you can trust the call's output (0-3)

  python3 strip_one.py session.jsonl                     # label from filename
  python3 strip_one.py session.jsonl --label pd1         # writes pd1.svg
  python3 strip_one.py a.jsonl b.jsonl --label bare spec # two rows, one figure
  python3 strip_one.py J=run_j/session.jsonl K=run_k/session.jsonl
  python3 strip_one.py session.jsonl --print             # sequences to stdout
  python3 strip_one.py session.jsonl -o /tmp/fig.svg
  python3 strip_one.py session.jsonl --no-trust          # flat borders
  python3 strip_one.py --selftest                        # classifier tests

BINS (fill) — hue says whose machine, lightness says how deep in the pipeline.

  setup             #B4B2A9   skill load, --help, config, which
  paperclip search  #66CCFF   search, searches, lookup
  paperclip read    #0080FF   grep, scan, sql, export, cat, head/tail,
                              ls, tree, wc, sed, awk, jq, sort/uniq/cut/tr
  paperclip analysis #185FA5  map, reduce, filter, ask-image
  local read        #FFCC66   pdftotext, pdfinfo, the Read tool
  local work        #FF8000   everything else on your own machine

Every border is drawn in one near-black ink, so border style reads as a
single channel independent of fill.

TRUST (border) — orthogonal to bin, so it gets its own visual channel.

  0  no border      nothing citable came back at all
  1  dashed         model-generated output, cites nothing by itself
  2  solid          a document is identified - which document, not where
  3  double stroke  result contains line-addressed source text (L13: ...)
                    Means the call came back holding text you could cite,
                    NOT that any claim was verified against it. That is a
                    separate, per-claim check this script does not attempt.

A red diagonal still marks a failed call, from the log's own is_error or an
error token in the result text.

Trust is assigned by rule in trust_for() — one function, edit it in one place.
"""

import argparse, json, os, re, sys

PITCH = 18
SQ = 14
X0 = 62
ROW_H = 36
Y0 = 60

# (fill, ink). Ink contrasts against its own fill so the border pattern stays
# legible on both the pale and the dark members of each family.
INK = "#1A1D19"

# fill only - every border uses INK, so the trust channel reads as one thing
STYLE = {
    "setup":       ("#B4B2A9", INK),
    "pc_search":   ("#66CCFF", INK),
    "pc_read":     ("#0080FF", INK),
    "pc_analyze":  ("#185FA5", INK),
    "local_read":  ("#FFCC66", INK),
    "local_work":  ("#FF8000", INK),
}
LEGEND = [("setup", "setup"),
          ("pc_search", "paperclip search"),
          ("pc_read", "paperclip read"),
          ("pc_analyze", "paperclip analysis"),
          ("local_read", "local read"),
          ("local_work", "local work")]
TRUST_LEGEND = [(0, "no locator"), (1, "model-generated"),
                (2, "document"), (3, "line")]
FAIL = "#E24B4A"
MUTED = "#5E6B63"


# ---------------------------------------------------------------- parsing

def load(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def results_index(events):
    idx = {}
    for d in events:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                cc = b.get("content")
                txt = ("".join(x.get("text", "") for x in cc
                               if isinstance(x, dict) and x.get("type") == "text")
                       if isinstance(cc, list) else (cc or ""))
                idx[b.get("tool_use_id")] = (txt, bool(b.get("is_error")))
    return idx


# ------------------------------------------------------------ classifying

SEARCH_SUBS = {"search", "searches", "lookup"}
ANALYZE_SUBS = {"map", "reduce", "filter", "ask-image", "ask_image"}
READ_SUBS = {"grep", "scan", "sql", "export", "cat", "head", "tail", "ls",
             "tree", "wc", "cd", "pwd", "sort", "uniq", "cut", "tr", "sed",
             "awk", "jq", "results", "pull"}
SETUP_SUBS = {"skill", "install", "config", "login", "logout", "update"}
LOCAL_READ = ("pdftotext", "pdfinfo", "pdftk")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

PRIORITY = ["pc_analyze", "pc_search", "pc_read", "local_read", "setup", "local_work"]

SEGMENT_SPLIT = re.compile(r"\|\||&&|\||;|\n")
# Heredoc bodies are data, not commands - a python script or JSON schema piped
# into a file must not be scanned for subcommand names. Stripped before split.
HEREDOC = re.compile(r"<<-?['\"]?(\w+)['\"]?\n.*?\n\s*\1\s*(?=\n|$)", re.S)
CORPUS_PATH = re.compile(r"/(papers|fda|clinicaltrials|workspace)/")


def _segments(s):
    s = HEREDOC.sub("\n", s)
    return [seg.strip() for seg in SEGMENT_SPLIT.split(s) if seg.strip()]


def _sub_kind(tok):
    tok = tok.strip("'\"`")
    if tok in SEARCH_SUBS:
        return "pc_search"
    if tok in ANALYZE_SUBS:
        return "pc_analyze"
    if tok in READ_SUBS:
        return "pc_read"
    if tok in SETUP_SUBS:
        return "setup"
    return None


def _inner_script(seg):
    """Pull the quoted script out of `paperclip bash '...'`."""
    m = re.search(r"paperclip\s+bash\s+(['\"])(.*?)\1", seg, re.S)
    return m.group(2) if m else None


RUN_FILE = re.compile(
    r"(?:^|\s)(?:\./|(?:ba|z)?sh\s+|python3?\s+|source\s+|\.\s+)([\w./~-]+\.(?:sh|py|zsh|bash))\b")


def _script_bodies(cmd, known, depth=0):
    """Bodies of any scripts this command executes, if the log showed them.

    The session log contains the text of every script the agent wrote. A command
    that runs one of those files is executing bytes we already have, so they are
    resolved and classified like any other segment. Nothing is inferred: a body
    is only substituted when its exact filename was written earlier in the same
    session. Depth-limited, since a script may call another.
    """
    if not known or depth > 2:
        return []
    out = []
    for m in RUN_FILE.finditer(cmd or ""):
        body = known.get(os.path.basename(m.group(1)))
        if body:
            out.append(body)
            out.extend(_script_bodies(body, known, depth + 1))
    return out


def classify(name, cmd, known=None):
    """Return the bin for one tool call.

    Paperclip calls are found by scanning each shell segment for a literal
    `paperclip <sub>`, or, inside `paperclip bash '...'`, for a bare <sub>.
    A segment that is not itself a paperclip invocation is local work, so
    `paperclip grep ... | head -20` is a paperclip read with a local head.
    Where a call spans several bins, PRIORITY decides how it is drawn.
    """
    if name == "Skill":
        return "setup"
    if name == "Read":
        return "local_read"
    if name in WRITE_TOOLS:
        return "local_work"
    if not cmd:
        return "local_work"


    kinds = set()

    for body in _script_bodies(cmd, known):
        for seg in _segments(body):
            toks = seg.split()
            if toks and toks[0].strip("'\"`") == "paperclip" and len(toks) > 1:
                kinds.add("setup" if "--help" in seg
                          else (_sub_kind(toks[1]) or "local_work"))

    inner = _inner_script(cmd)
    if inner is not None:
        for iseg in _segments(inner):
            toks = iseg.split()
            kinds.add((_sub_kind(toks[0]) if toks else None) or "local_work")
    else:
        for seg in _segments(cmd):
            toks = seg.split()
            if toks and toks[0].strip("'\"`") == "paperclip" and len(toks) > 1:
                kinds.add("setup" if "--help" in seg
                          else (_sub_kind(toks[1]) or "local_work"))
            elif any(t in seg for t in LOCAL_READ):
                kinds.add("local_read")
            elif toks and toks[0] == "which":
                kinds.add("setup")
            else:
                kinds.add("local_work")

    for k in PRIORITY:
        if k in kinds:
            return k
    return "local_work"


# ----------------------------------------------------------------- trust

# Two structural signals, both read off the text itself. Neither consults the
# bin, so nothing is exempt or privileged by category.
#
#   LINE_ADDR - a line address, as returned by `grep -n` / `cat -n` against the
#               corpus: "L13: Although PD-1 expression ...". Colon required so a
#               bare mention of L13 in prose does not qualify.
#   DOC_ID    - a document identifier: PMC/NCT accession, a corpus doc id, a DOI,
#               a corpus path, or a local document file.
LINE_ADDR = re.compile(r"(^|[\s\[(|])L\d+\s*:")
DOC_ID = re.compile(
    r"\b(?:PMC\d{4,}|NCT\d{6,}|(?:bio|med|arx|fda|tri|usr)_[0-9a-f]{6,}"
    r"|10\.\d{4,9}/[^\s,;)\]]+)\b"
    r"|/(?:papers|fda|clinicaltrials|workspace)/"
    r"|\.(?:pdf|PDF)\b")


def trust_for(kind, name, cmd, rtext, failed=False):
    """Trust level 0-3 for one call, read off the RESULT, not the command.

    The question the border answers is: how precisely could a downstream claim
    point at where this came from?

      3  a line address came back - you can cite a location inside a document
      2  a document is identified - you can cite which document, not where
      1  the output was generated by a model, so it cites nothing by itself
      0  nothing citable came back at all

    Nothing is keyed to a category, so calls in the same bin can differ.
    `paperclip map --help` scores 0 - usage text names no document. But
    `paperclip skill` scores 2, because the skill file IS a document the agent
    consulted and you can name it. A local `pdftotext marim2010.pdf` scores 2
    for the same reason: the command names what was read.

    NOT a verification claim. Level 3 means a locator came back; nothing here
    checks that a claim is supported by what sits at that locator.
    """
    if rtext is None or failed or not rtext.strip():
        return 0
    if kind == "pc_analyze" or name in WRITE_TOOLS:
        return 1
    if LINE_ADDR.search(rtext):
        return 3
    if DOC_ID.search(rtext) or DOC_ID.search(cmd or ""):
        return 2
    return 0


SCRIPT_HEREDOC = re.compile(r"cat\s*>\s*([\w./~-]+\.(?:sh|py|zsh|bash))\s*<<-?['\"]?(\w+)['\"]?\n(.*?)\n\s*\2\s*(?=\n|$)", re.S)


def sequence(path):
    ev = load(path)
    idx = results_index(ev)
    known = {}
    out = []
    for d in ev:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            name = b.get("name")
            inp = b.get("input") or {}
            cmd = inp.get("command", "")
            if name in WRITE_TOOLS:
                fp = inp.get("file_path") or inp.get("path") or ""
                body = inp.get("content") or inp.get("new_string") or ""
                if fp.endswith((".sh", ".py", ".zsh", ".bash")) and body:
                    known[os.path.basename(fp)] = body
            for hm in SCRIPT_HEREDOC.finditer(cmd or ""):
                known[os.path.basename(hm.group(1))] = hm.group(3)
            rtext, err = idx.get(b.get("id"), (None, False))
            failed = bool(err) or (rtext is not None and
                                   (("Results not found" in rtext) or ("ERR:" in rtext)))
            kind = classify(name, cmd, known)
            out.append((kind, failed, trust_for(kind, name, cmd, rtext, failed)))
    return out


# --------------------------------------------------------------- drawing

def _square(x, y, fill, ink, trust, show_trust):
    """One square: fill for the bin, border pattern for the trust level."""
    o = []
    if not show_trust:
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s" '
                 'stroke="%s" stroke-width="0.6"/>' % (x, y, SQ, SQ, fill, ink))
        return o
    if trust == 0:
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
                 % (x, y, SQ, SQ, fill))
    elif trust == 1:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" '
                 'fill="%s" stroke="%s" stroke-width="1.3" '
                 'stroke-dasharray="2.6 2"/>'
                 % (x + 0.65, y + 0.65, SQ - 1.3, SQ - 1.3, fill, ink))
    elif trust == 2:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" '
                 'fill="%s" stroke="%s" stroke-width="1.4"/>'
                 % (x + 0.7, y + 0.7, SQ - 1.4, SQ - 1.4, fill, ink))
    else:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" '
                 'fill="%s" stroke="%s" stroke-width="1.4"/>'
                 % (x + 0.7, y + 0.7, SQ - 1.4, SQ - 1.4, fill, ink))
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" '
                 'fill="none" stroke="%s" stroke-width="0.9"/>'
                 % (x + 3.4, y + 3.4, SQ - 6.8, SQ - 6.8, ink))
    return o


def svg(rows, show_trust=True):
    widest = max((len(s) for _, s in rows), default=0)
    right = X0 + widest * PITCH + 44
    width = max(720, right)
    legend_y = Y0 + len(rows) * ROW_H + 16
    trust_y = legend_y + 26
    height = (trust_y if show_trust else legend_y) + 26

    o = []
    o.append('<svg width="100%%" viewBox="0 0 %d %d" role="img" '
             'xmlns="http://www.w3.org/2000/svg" '
             'font-family="system-ui, sans-serif">' % (width, height))
    o.append("<title>Agent call sequences per run</title>")
    o.append("<desc>Each row is one run. Each square is one tool call in order. "
             "Fill colour is the kind of call; border style is how much the "
             "output can be trusted. A red slash marks a failed call.</desc>")

    for i, (label, seq) in enumerate(rows):
        y = Y0 + i * ROW_H
        cy = y + SQ / 2 + 4
        o.append('<text x="40" y="%.1f" font-size="14" font-weight="500" '
                 'fill="%s">%s</text>' % (cy, INK, label))
        if not seq:
            o.append('<text x="%d" y="%.1f" font-size="12" fill="%s">'
                     'no tool calls found</text>' % (X0, cy, MUTED))
            continue
        slashes = []
        for j, (kind, failed, trust) in enumerate(seq):
            x = X0 + j * PITCH
            fill, ink = STYLE.get(kind, STYLE["local_work"])
            o.extend(_square(x, y, fill, ink, trust, show_trust))
            if failed:
                slashes.append("M%.1f %.1fL%.1f %.1f"
                               % (x + 2, y + 2, x + SQ - 2, y + SQ - 2))
        if slashes:
            o.append('<path d="%s" stroke="%s" stroke-width="1.8" '
                     'stroke-linecap="round" fill="none"/>' % ("".join(slashes), FAIL))
        o.append('<text x="%d" y="%.1f" font-size="12" fill="%s">%d</text>'
                 % (X0 + len(seq) * PITCH + 8, cy, MUTED, len(seq)))

    x = 40
    for kind, text in LEGEND:
        fill, ink = STYLE[kind]
        o.append('<rect x="%d" y="%d" width="12" height="12" rx="2" fill="%s" '
                 'stroke="%s" stroke-width="0.6"/>' % (x, legend_y, fill, ink))
        o.append('<text x="%d" y="%d" font-size="12" fill="%s">%s</text>'
                 % (x + 17, legend_y + 10, MUTED, text))
        x += 25 + len(text) * 6.4
    fill, ink = STYLE["pc_analyze"]
    o.append('<rect x="%d" y="%d" width="12" height="12" rx="2" fill="%s" '
             'stroke="%s" stroke-width="0.6"/>' % (x, legend_y, fill, ink))
    o.append('<path d="M%d %dL%d %d" stroke="%s" stroke-width="1.8" '
             'stroke-linecap="round" fill="none"/>'
             % (x + 2, legend_y + 2, x + 10, legend_y + 10, FAIL))
    o.append('<text x="%d" y="%d" font-size="12" fill="%s">failed</text>'
             % (x + 17, legend_y + 10, MUTED))

    if show_trust:
        o.append('<text x="40" y="%d" font-size="11" fill="%s" '
                 'letter-spacing="0.4">TRUST</text>' % (trust_y + 10, MUTED))
        x = 92
        for lvl, text in TRUST_LEGEND:
            o.extend(_square(x, trust_y, "#FFFFFF", INK, lvl, True))
            o.append('<text x="%d" y="%d" font-size="12" fill="%s">%d · %s</text>'
                     % (x + SQ + 5, trust_y + 11, MUTED, lvl, text))
            x += SQ + 26 + len(text) * 6.4

    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------- cli

def default_label(path):
    """Session filenames are UUIDs, so fall back to the parent directory."""
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    if stem in ("session", "") or len(stem) > 24:
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if parent:
            return parent
    return stem


SELFTEST = [
    # (tool name, command, result text, is_error, want_kind, want_trust)
    ("Skill", '{"skill": "paperclip"}', "Launching skill: paperclip", False, "setup", 0),
    ("Bash", "paperclip map --help", "usage: map ...", False, "setup", 0),
    ("Bash", "which paperclip", "/usr/local/bin/paperclip", False, "setup", 0),
    ("Bash", 'paperclip search -s pmc "PD-1" -n 10',
     "Found 10 papers [s_384608a4]\n  1. CK2B induces...\n     PMC12021095 - PMC - 2025", False, "pc_search", 2),
    ("Bash", 'paperclip search "zzz" -n 5', "Found 0 papers", False, "pc_search", 0),
    ("Bash", 'paperclip grep -n "exhaust" /papers/PMC1/content.lines',
     "L13:Although PD-1 expression by antigen specific CD8 T cells", False, "pc_read", 3),
    ("Bash", 'paperclip grep -n "zzz" /papers/PMC1/content.lines', "", False, "pc_read", 0),
    ("Bash", "paperclip cat /papers/PMC1/meta.json",
     '{"title": "...", "doi": "10.1371/journal.pone.0015263"}', False, "pc_read", 2),
    ("Bash", 'paperclip sql "SELECT title FROM documents LIMIT 5"', "title | doi", False, "pc_read", 0),
    ("Bash", 'paperclip map --from s_abc "What methods?"', "Map complete: 3/3 papers", False, "pc_analyze", 1),
    ("Bash", 'paperclip map --from s_1 "q"', "ERR: Results not found", True, "pc_analyze", 0),
    ("Bash", "paperclip bash 'search \"folding\" | grep \"deep\"'", "Found 4 papers", False, "pc_search", 0),
    ("Bash", "paperclip bash 'cd /papers/bio_1/ && ask_image fig1.tif'", "The figure shows ...", False, "pc_analyze", 1),
    ("Bash", "paperclip bash 'grep -i kinase /papers/bio_1/content.lines | sort -u'",
     "L88:kinase activity was measured", False, "pc_read", 3),
    ("Bash", "pdftotext paper.pdf out.txt", "", False, "local_read", 0),
    ("Bash", "pdftotext marim2010.pdf -", "Bone marrow cells were cultured", False, "local_read", 2),
    ("Read", '{"file_path": "/x/marim2010.pdf"}', "     1\tMethods", False, "local_read", 2),
    ("Write", "", "Wrote 71 lines to summary.txt", False, "local_work", 1),
    ("Bash", "python3 flatten.py > out.tsv", "wrote 17 rows", False, "local_work", 0),
    ("Bash", 'grep -c "M-CSF" out.tsv', "12", False, "local_work", 0),
    ("Bash", "cat missing.txt", None, False, "local_work", 0),
]


def selftest():
    bad = 0
    for name, cmd, rtext, failed, want_kind, want_trust in SELFTEST:
        kind = classify(name, cmd)
        trust = trust_for(kind, name, cmd, rtext, failed)
        ok = (kind == want_kind and trust == want_trust)
        bad += not ok
        print("%s %-11s t%d  %-46s | %s" % (
            "ok  " if ok else "FAIL", kind, trust,
            (cmd or "(no command)")[:46],
            "(no result)" if rtext is None else (rtext[:26] or "(empty)")))
    print("\n%s" % ("all pass" if not bad else "%d failures" % bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(
        description="Draw tool-call strips for named session logs.")
    ap.add_argument("sessions", nargs="*",
                    help="paths to session .jsonl files, or LABEL=path pairs")
    ap.add_argument("--label", nargs="+", default=None,
                    help="labels, in the same order as the sessions")
    ap.add_argument("-o", "--out", default=None,
                    help="output svg path (default: <first label>.svg)")
    ap.add_argument("--print", dest="show", action="store_true",
                    help="print sequences instead of writing svg")
    ap.add_argument("--no-trust", dest="trust", action="store_false",
                    help="draw uniform borders, bin colours only")
    ap.add_argument("--selftest", action="store_true",
                    help="run classifier + trust tests and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.sessions:
        ap.error("give at least one session .jsonl (or --selftest)")

    paths, labels = [], []
    for s in args.sessions:
        if "=" in s and not os.path.exists(s):
            lab, _, p = s.partition("=")
            labels.append(lab)
            paths.append(p)
        else:
            paths.append(s)
            labels.append(None)

    if args.label:
        if len(args.label) != len(paths):
            print("error: %d labels for %d sessions"
                  % (len(args.label), len(paths)), file=sys.stderr)
            return 1
        labels = list(args.label)

    labels = [l if l else default_label(p) for l, p in zip(labels, paths)]

    rows = []
    for label, p in zip(labels, paths):
        if not os.path.exists(p):
            print("error: no such file: %s" % p, file=sys.stderr)
            return 1
        rows.append((label, sequence(p)))

    if args.show:
        for label, seq in rows:
            if not seq:
                print("%-12s (no tool calls found)" % label)
                continue
            print("%-12s %2d  %s" % (label, len(seq),
                  " ".join("%s%d%s" % (k, t, "x" if f else "") for k, f, t in seq)))
            tally = {}
            for k, f, t in seq:
                tally[k] = tally.get(k, 0) + 1
            print("%-12s     %s" % ("", "  ".join(
                "%s=%d" % (k, tally[k]) for k in PRIORITY if k in tally)))
        return 0

    out = args.out or (labels[0] + ".svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg(rows, show_trust=args.trust))
    print("wrote", out)
    for label, seq in rows:
        print("  %-12s %d calls%s" % (label, len(seq),
              "" if seq else "  (no tool calls found)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
