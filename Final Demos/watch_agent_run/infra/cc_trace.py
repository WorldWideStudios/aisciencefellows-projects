#!/usr/bin/env python3
"""
cc_trace.py — deterministic action+outcome trace from a Claude Code session log.

WHAT THIS IS
------------
Reads a Claude Code session .jsonl (the files under ~/.claude/projects/<proj>/*.jsonl)
and emits the ordered list of tool calls, each paired with its result.

TRUST CONTRACT (read this — it's the whole point of the tool)
------------------------------------------------------------
Every column this script prints is a VERBATIM substring of the log, or a count
derived by structural parsing. Nothing is model-generated. Specifically:

  * ORDER      — falls out of reading the file top-to-bottom. A .jsonl is
                 append-only; line N was written before line N+1. No sorting,
                 no timestamp reconstruction. Chronology is free and exact.
  * TOOL/INPUT — pulled from `message.content[].type == "tool_use"` blocks.
                 The command / input is printed verbatim (clipped for width in
                 compact mode, with the clip marked; --full prints it whole).
  * RESULT     — pulled from the paired `tool_result` block by tool_use_id.
                 Compact mode shows the FIRST non-empty line verbatim plus a
                 "(+N more lines)" count. --full prints the whole result.
                 The salience rule is STRUCTURAL (first line + line count), not
                 semantic. It never summarizes or interprets the result.

  * ERROR FLAGS — two distinct signals, never conflated:
      [exec-error]  the log's own `is_error: true` on the tool_result.
                    This is the trustworthy signal: the tool call itself failed.
      [out-signature] the result TEXT contains an error-like token (err:, exit N,
                    unavailable, not found, traceback, failed). This is a
                    convenience flag, NOT a verdict — a tool can run fine and
                    print the word "error", or fail without it. Always read the
                    full result (--full) before trusting an [out-signature].

If you ever want a human-readable *interpretation* of a result ("the map found
modest ORR across 12 papers"), that is a separate, model-generated layer this
script deliberately does NOT provide. Keep that line bright.

USAGE
-----
  python3 cc_trace.py SESSION.jsonl                # compact action+outcome table
  python3 cc_trace.py SESSION.jsonl --full         # verbatim full input + result
  python3 cc_trace.py SESSION.jsonl --md           # markdown table (pasteable)
  python3 cc_trace.py SESSION.jsonl --only Bash    # filter to one tool
  python3 cc_trace.py SESSION.jsonl --width 120    # set compact clip width
  python3 cc_trace.py SESSION.jsonl --calls        # ordered call list only, no results
"""

import argparse, json, sys

# Structural error signatures scanned in result TEXT. Convenience flag only —
# see TRUST CONTRACT above. Edit freely; matching is case-insensitive substring.
OUT_SIGNATURES = ("err:", "error:", "exit 1", "exit 2", "exit 3",
                  "unavailable", "not found", "traceback", "failed",
                  "no such", "permission denied", "cannot ")


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A corrupt line is itself a fact worth surfacing, not hiding.
                events.append({"_parse_error": line[:200]})
    return events


def result_text(block):
    """Extract verbatim text from a tool_result content block."""
    c = block.get("content")
    if isinstance(c, list):
        return "".join(
            x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"
        )
    return c if isinstance(c, str) else json.dumps(c)


def build_result_index(events):
    """Map tool_use_id -> (verbatim_text, is_error_flag)."""
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
                idx[b.get("tool_use_id")] = (result_text(b), bool(b.get("is_error")))
    return idx


def input_oneline(name, inp):
    """Best-effort single-line VERBATIM rendering of a tool input."""
    if name == "Bash":
        return " ".join(inp.get("command", "").split())
    # Prefer common informative scalar fields, else compact JSON (still verbatim).
    for k in ("command", "file_path", "path", "pattern", "url", "query", "prompt", "description"):
        if k in inp and isinstance(inp[k], str):
            return " ".join(inp[k].split())
    return json.dumps(inp, ensure_ascii=False)


def out_signatures(text):
    low = text.lower()
    return [s for s in OUT_SIGNATURES if s in low]


def iter_calls(events, result_idx):
    """Yield (index, name, input_dict, result_text, is_error) in file order."""
    n = 0
    for d in events:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                n += 1
                rid = b.get("id")
                rtext, ierr = result_idx.get(rid, (None, False))
                yield n, b.get("name", "?"), b.get("input", {}), rtext, ierr


def clip(s, width):
    if len(s) <= width:
        return s
    return s[: width - 1] + "…"


def flags_for(rtext, ierr):
    flags = []
    if ierr:
        flags.append("exec-error")
    if rtext:
        sigs = out_signatures(rtext)
        if sigs:
            flags.append("out-signature:" + "/".join(sigs[:2]))
    return flags


def render_compact(calls, width, only):
    for n, name, inp, rtext, ierr in calls:
        if only and name != only:
            continue
        line = input_oneline(name, inp)
        clipped = clip(line, width)
        mark = "  [+%d chars]" % (len(line) - len(clipped) + 1) if clipped != line else ""
        print(f"{n:3d}. [{name}] {clipped}{mark}")
        if rtext is None:
            print("       result: (no result in log — call may be last/interrupted)")
            continue
        lines = [ln for ln in rtext.splitlines() if ln.strip()]
        first = lines[0] if lines else "(empty result)"
        extra = f"  (+{len(lines)-1} more lines)" if len(lines) > 1 else ""
        fl = flags_for(rtext, ierr)
        flagstr = ("   ⚑ " + " ".join(fl)) if fl else ""
        print(f"       result: {clip(first, width)}{extra}{flagstr}")


def render_full(calls, only):
    for n, name, inp, rtext, ierr in calls:
        if only and name != only:
            continue
        print("=" * 78)
        print(f"[{n}] {name}")
        print("-" * 78)
        print("INPUT (verbatim):")
        if name == "Bash":
            print(inp.get("command", ""))
        else:
            print(json.dumps(inp, indent=2, ensure_ascii=False))
        fl = flags_for(rtext, ierr)
        print("\nRESULT (verbatim)" + (("   FLAGS: " + " ".join(fl)) if fl else "") + ":")
        print(rtext if rtext is not None else "(no result in log)")
        print()


def render_md(calls, width, only):
    print("| # | Tool | Input (verbatim) | Result (first line, verbatim) | Flags |")
    print("|--:|------|------------------|-------------------------------|-------|")
    for n, name, inp, rtext, ierr in calls:
        if only and name != only:
            continue
        line = input_oneline(name, inp).replace("|", "\\|")
        if rtext is None:
            first, extra = "(no result in log)", ""
        else:
            lines = [ln for ln in rtext.splitlines() if ln.strip()]
            first = (lines[0] if lines else "(empty)").replace("|", "\\|")
            extra = f" (+{len(lines)-1})" if len(lines) > 1 else ""
        fl = flags_for(rtext, ierr)
        print(f"| {n} | {name} | `{clip(line, width)}` | {clip(first, width)}{extra} | {' '.join(fl)} |")


def render_calls_only(calls, width, only):
    for n, name, inp, rtext, ierr in calls:
        if only and name != only:
            continue
        print(f"{n:3d}. [{name}] {clip(input_oneline(name, inp), width)}")


def main():
    ap = argparse.ArgumentParser(description="Deterministic Claude Code session trace.")
    ap.add_argument("session", help="path to a Claude Code session .jsonl")
    ap.add_argument("--full", action="store_true", help="verbatim full input + result per call")
    ap.add_argument("--md", action="store_true", help="markdown table output")
    ap.add_argument("--calls", action="store_true", help="ordered call list only (no results)")
    ap.add_argument("--only", metavar="TOOL", help="filter to one tool name (e.g. Bash)")
    ap.add_argument("--width", type=int, default=96, help="clip width for compact/md (default 96)")
    args = ap.parse_args()

    events = load_events(args.session)
    result_idx = build_result_index(events)
    calls = list(iter_calls(events, result_idx))

    # Header — all counts are structural.
    sid = next((d.get("sessionId") for d in events if isinstance(d, dict) and d.get("sessionId")), None)
    n_exec = sum(1 for _, _, _, rt, ie in calls if ie)
    n_sig = sum(1 for _, _, _, rt, ie in calls if rt and out_signatures(rt) and not ie)
    by_tool = {}
    for _, name, _, _, _ in calls:
        by_tool[name] = by_tool.get(name, 0) + 1
    tool_break = ", ".join(f"{k}×{v}" for k, v in sorted(by_tool.items(), key=lambda x: -x[1]))

    print(f"# session: {sid or '(no sessionId field)'}")
    print(f"# events: {len(events)}   tool calls: {len(calls)}   ({tool_break})")
    print(f"# exec-errors (log is_error): {n_exec}   out-signatures only: {n_sig}")
    print(f"# order = file order (append-only .jsonl); nothing below is interpreted")
    print()

    if args.full:
        render_full(calls, args.only)
    elif args.md:
        render_md(calls, args.width, args.only)
    elif args.calls:
        render_calls_only(calls, args.width, args.only)
    else:
        render_compact(calls, args.width, args.only)


if __name__ == "__main__":
    main()
