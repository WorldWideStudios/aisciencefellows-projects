import marimo

__generated_with = "0.23.15"
app = marimo.App(width="full")


@app.cell
def _():
    import json
    import sys
    from pathlib import Path

    import marimo as mo

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

    import adk_usage
    import watch_execution as watch

    BEADS_JSONL = PROJECT_ROOT / ".beads" / "issues.jsonl"
    RESULTS_DIR = PROJECT_ROOT / "pipeline" / "results"
    INPUTS_DIR = PROJECT_ROOT / "inputs"
    return (
        BEADS_JSONL,
        INPUTS_DIR,
        PROJECT_ROOT,
        RESULTS_DIR,
        adk_usage,
        json,
        mo,
        watch,
    )


@app.cell
def _(mo):
    # Palette: the dataviz reference instance, validated for this use — all checks
    # PASS in both modes on the adjacent pairlist. Light-mode aqua/yellow sit below
    # 3:1 on the surface, so every chart using them ships direct labels AND a table
    # (the relief rule). Roles, not raw hex, are referenced below so the dark values
    # swap in one place.
    CSS = """
    <style>
    .viz { color-scheme: light;
      --surface-1:#fcfcfb; --plane:#f9f9f7;
      --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
      --grid:#e1e0d9; --axis:#c3c2b7;
      --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
      --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --critical:#d03b3b;
    }
    @media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) .viz {
      color-scheme: dark;
      --surface-1:#1a1a19; --plane:#0d0d0d;
      --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
      --grid:#2c2c2a; --axis:#383835;
      --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    } }
    :root[data-theme="dark"] .viz { color-scheme: dark;
      --surface-1:#1a1a19; --plane:#0d0d0d;
      --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
      --grid:#2c2c2a; --axis:#383835;
      --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    }
    .viz { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
           color: var(--ink); }
    .viz .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
    .viz .tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }
    .viz .tile { background:var(--surface-1); border:1px solid var(--grid); border-radius:10px;
                 padding:13px 15px; }
    .viz .tile .k { font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
                    color:var(--muted); font-weight:650;
                    font-family:ui-monospace,"SF Mono",Menlo,monospace; }
    .viz .tile .v { font-size:26px; font-weight:750; letter-spacing:-.02em; margin-top:5px;
                    font-variant-numeric:tabular-nums; }
    .viz .tile .s { font-size:11.5px; color:var(--ink-2); margin-top:3px; }
    .viz .card { background:var(--surface-1); border:1px solid var(--grid); border-radius:10px;
                 padding:16px 18px; margin-top:12px; }
    .viz h3 { font-size:12px; letter-spacing:.07em; text-transform:uppercase; color:var(--ink-2);
              margin:0 0 10px; font-weight:700;
              font-family:ui-monospace,"SF Mono",Menlo,monospace; }
    .viz .note { font-size:11.5px; color:var(--muted); line-height:1.55; margin-top:9px; }
    .viz table.t { border-collapse:collapse; width:100%; font-size:12.5px;
                   font-variant-numeric:tabular-nums; }
    .viz table.t th { text-align:left; font-size:10px; letter-spacing:.06em; text-transform:uppercase;
                      color:var(--muted); border-bottom:1.5px solid var(--axis); padding:6px 9px;
                      font-family:ui-monospace,Menlo,monospace; }
    .viz table.t td { padding:6px 9px; border-bottom:1px solid var(--grid); }
    .viz .swatch { display:inline-block; width:9px; height:9px; border-radius:2.5px;
                   margin-right:6px; vertical-align:baseline; }
    .viz .legend { display:flex; flex-wrap:wrap; gap:14px; font-size:11.5px; color:var(--ink-2);
                   margin-top:9px; }
    .viz .pill { display:inline-block; padding:1.5px 8px; border-radius:20px; font-size:10.5px;
                 font-weight:700; font-family:ui-monospace,Menlo,monospace; }
    </style>
    """
    mo.Html(CSS)
    return (CSS,)


@app.cell
def _(CSS, mo):
    mo.Html(CSS + """
    <div class="viz">
      <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
                  font-family:ui-monospace,Menlo,monospace;font-weight:650">
        TEM-1 CFPS screening bench
      </div>
      <div style="font-size:27px;font-weight:800;letter-spacing:-.025em;margin:5px 0 4px">
        Campaign provenance
      </div>
      <div style="font-size:13px;color:var(--ink-2);max-width:74ch;line-height:1.6">
        Every physical run, planned or not, finished or not — plus what the agent layer
        cost to drive it. Read-only: rounds come from the beads DAG export, runs from
        <span class="mono">data/logs/</span>, tokens from ADK's own session store.
      </div>
    </div>
    """)
    return


@app.cell
def _(BEADS_JSONL, PROJECT_ROOT, json, mo):
    # Read the LIVE bd database, not `.beads/issues.jsonl`. That file is a passive
    # export and was observed dropping issues that exist in the DB (an unplanned
    # round and several execution children), which made attributed runs render as
    # orphans. A provenance view inheriting a lossy export is worse than one that
    # fails loudly, so the export is only a fallback and says so when used.
    import subprocess as _sp

    all_issues, export_state = {}, ""
    try:
        _p = _sp.run(["bd", "list", "--json", "--all"], capture_output=True,
                     text=True, cwd=PROJECT_ROOT, timeout=30)
        if _p.returncode == 0:
            for _rec in json.loads(_p.stdout):
                all_issues[_rec["id"]] = _rec
            export_state = f"live `bd` database · {len(all_issues)} issue(s)"
        else:
            export_state = f"FALLBACK to issues.jsonl — `bd list` failed: {_p.stderr.strip()[:100]}"
    except Exception as _e:
        export_state = f"FALLBACK to issues.jsonl — {type(_e).__name__}"

    if not all_issues:
        if not BEADS_JSONL.exists() or not BEADS_JSONL.read_text().strip():
            mo.stop(True, mo.md("No beads yet — plan a round first (`pipeline/agents/plan_agent.py`)."))
        for line in BEADS_JSONL.read_text().splitlines():
            if line.strip():
                _rec = json.loads(line)
                all_issues[_rec["id"]] = _rec

    def label_value(rec, prefix):
        for lbl in rec.get("labels", []):
            if lbl.startswith(prefix):
                return lbl[len(prefix):]
        return None

    rounds = {
        rid: _rec for rid, _rec in all_issues.items()
        if _rec.get("issue_type") == "task" and "." not in rid and label_value(_rec, "assay:")
    }
    return all_issues, export_state, label_value, rounds


@app.cell
def _(all_issues, watch):
    # Physical runs come from the filesystem, not from beads — a run that reached
    # hardware without being planned still has a folder, and that is exactly the
    # case this pane exists to make visible.
    runs = watch.discover_executions()
    # An execution_id can sit in two places: on a child bead written by
    # link_execution ("<round>.<n>"), or on the round itself when the round was
    # created *from* that execution (an unplanned run). Read both — looking at
    # only the children silently reports attributed runs as orphans.
    linked = {}
    for _v in all_issues.values():
        _eid = (_v.get("metadata") or {}).get("execution_id")
        if not _eid:
            continue
        linked[_eid] = _v["id"].split(".")[0]
    return linked, runs


@app.cell
def _(CSS, adk_usage, export_state, label_value, linked, mo, rounds, runs):
    usage = adk_usage.summarize()
    _t = usage["totals"]
    _stopped = [r for r in runs if r.get("complete") is False]
    _orphans = [r for r in runs if r["execution_id"] not in linked]
    _decided = [r for r in rounds.values() if label_value(r, "stage:") == "decided"]

    def _tile(k, v, s, color=None):
        c = f"color:{color}" if color else ""
        return (f'<div class="tile"><div class="k">{k}</div>'
                f'<div class="v" style="{c}">{v}</div><div class="s">{s}</div></div>')

    mo.Html(CSS + f"""
    <div class="viz"><div class="tiles">
      {_tile("Rounds", len(rounds), f"{len(_decided)} decided")}
      {_tile("Physical runs", len(runs), "executions on disk")}
      {_tile("Stopped early", len(_stopped),
             "before the final step", "var(--critical)" if _stopped else None)}
      {_tile("Unattributed", len(_orphans),
             "no round linked", "var(--warn)" if _orphans else "var(--good)")}
      {_tile("Agent tokens", f"{_t['total']:,}", f"{_t['calls']} model calls")}
      {_tile("Est. agent cost", f"${_t['cost_usd']:.4f}", "tokens x local rate card")}
    </div>
    <div class="note">beads export {export_state} · rounds and links below reflect the
    live <span class="mono">bd</span> database.</div>
    </div>
    """)
    return (usage,)


@app.cell
def _(CSS, mo, usage):
    # FORM: one horizontal stacked bar — the job is composition of a single total,
    # not comparison across categories. Direct labels on every segment + the table
    # below satisfy the relief rule for the two light-mode slots under 3:1.
    _t = usage["totals"]
    _fresh = max(_t["prompt"] - _t["cached"], 0)
    _parts = [
        ("Prompt (fresh)", _fresh, "var(--s1)"),
        ("Prompt (cached)", _t["cached"], "var(--s3)"),
        ("Thinking", _t["thoughts"], "var(--s4)"),
        ("Output", _t["candidates"], "var(--s2)"),
    ]
    _sum = sum(p[1] for p in _parts) or 1

    _segs, _x = [], 0.0
    for _name, _val, _col in _parts:
        _w = 100 * _val / _sum
        # 2px surface gap between adjacent fills, per the mark spec.
        _segs.append(
            f'<div title="{_name}: {_val:,} tokens" style="position:absolute;left:{_x}%;'
            f'width:calc({_w}% - 2px);top:0;height:100%;background:{_col};border-radius:4px"></div>'
        )
        _x += _w

    _rows = "".join(
        f'<tr><td><span class="swatch" style="background:{c}"></span>{n}</td>'
        f'<td class="mono" style="text-align:right">{v:,}</td>'
        f'<td class="mono" style="text-align:right;color:var(--ink-2)">{100*v/_sum:.1f}%</td></tr>'
        for n, v, c in _parts
    )
    _legend = "".join(
        f'<span><span class="swatch" style="background:{c}"></span>{n} '
        f'<span class="mono" style="color:var(--muted)">{100*v/_sum:.0f}%</span></span>'
        for n, v, c in _parts
    )

    _agent_max = max((a["total"] for a in usage["by_agent"]), default=1) or 1
    _agent_bars = "".join(
        f'<tr><td>{a["author"] or "(unknown)"}</td>'
        f'<td style="width:52%"><div style="position:relative;height:15px">'
        f'<div style="position:absolute;left:0;top:2px;height:11px;border-radius:4px;'
        f'width:{100*a["total"]/_agent_max:.1f}%;background:var(--s1)"></div></div></td>'
        f'<td class="mono" style="text-align:right">{a["total"]:,}</td>'
        f'<td class="mono" style="text-align:right">${a["cost_usd"]:.4f}</td>'
        f'<td class="mono" style="text-align:right;color:var(--ink-2)">{a["calls"]}</td></tr>'
        for a in usage["by_agent"]
    )

    mo.Html(CSS + f"""
    <div class="viz">
      <div class="card">
        <h3>Agent token spend — {_t['total']:,} tokens · ${_t['cost_usd']:.4f}</h3>
        <div style="position:relative;height:26px;width:100%">{''.join(_segs)}</div>
        <div class="legend">{_legend}</div>
        <table class="t" style="margin-top:14px">
          <thead><tr><th>Component</th><th style="text-align:right">Tokens</th>
          <th style="text-align:right">Share</th></tr></thead>
          <tbody>{_rows}</tbody>
        </table>
        <div class="note">
          <b>Cost is computed here, not reported by the API.</b> {usage['cost_basis']}.
          Gemini returns token counts only — there is no price field in
          <span class="mono">usage_metadata</span>. Rates live in
          <span class="mono">pipeline/adk_usage.py</span> (list prices noted 2026-07);
          edit them there or set <span class="mono">PIPELINE_RATES</span>. Cache hit rate
          <b>{usage['cache_hit_rate']:.0%}</b> of prompt tokens, billed at the reduced rate.
          {"Traffic type: " + ", ".join(usage["traffic_types"]) if usage["traffic_types"]
           else "Traffic type not reported — these rates assume on-demand, not provisioned throughput."}
        </div>
      </div>

      <div class="card">
        <h3>By agent</h3>
        <table class="t">
          <thead><tr><th>Agent</th><th>Tokens</th><th style="text-align:right"></th>
          <th style="text-align:right">Cost</th><th style="text-align:right">Calls</th></tr></thead>
          <tbody>{_agent_bars}</tbody>
        </table>
        <div class="note">Bars share one scale; the coordinator delegates, so a sub-agent
        carrying the most tokens is the one doing the work, not the one misbehaving.</div>
      </div>
    </div>
    """)
    return


@app.cell
def _(CSS, linked, mo, runs):
    def _status_pill(r):
        if r.get("complete") is True:
            return '<span class="pill" style="background:var(--good);color:#fff">COMPLETE</span>'
        if r.get("complete") is False:
            return '<span class="pill" style="background:var(--critical);color:#fff">STOPPED</span>'
        return '<span class="pill" style="background:var(--grid);color:var(--ink-2)">UNKNOWN</span>'

    _rows = "".join(
        f'<tr>'
        f'<td class="mono" style="font-size:11px">{r["execution_id"].replace("exec_", "")}</td>'
        f'<td>{r.get("workflow_id") or "?"}</td>'
        f'<td class="mono" style="font-size:11px">{(r.get("started") or "")[:19]}</td>'
        f'<td>{_status_pill(r)}</td>'
        f'<td class="mono" style="font-size:11px">{r.get("last_checkpoint") or "—"}</td>'
        f'<td class="mono" style="font-size:11px">{r.get("source") or "app"}</td>'
        f'<td class="mono" style="font-size:11px">'
        f'{linked.get(r["execution_id"]) or "<span style=color:var(--warn)>UNATTRIBUTED</span>"}</td>'
        f'<td style="text-align:center">{"✓" if r.get("has_platereader_export") else "·"}</td>'
        f'</tr>'
        for r in runs
    )
    _n_orphan = sum(1 for r in runs if r["execution_id"] not in linked)

    mo.Html(CSS + f"""
    <div class="viz"><div class="card">
      <h3>Physical runs — {len(runs)} execution(s)</h3>
      <table class="t">
        <thead><tr><th>Execution</th><th>Workflow</th><th>Started</th><th>Outcome</th>
        <th>Last step</th><th>Source</th><th>Round</th><th>Reader</th></tr></thead>
        <tbody>{_rows or '<tr><td colspan=8 style="color:var(--muted)">no executions recorded yet</td></tr>'}</tbody>
      </table>
      <div class="note">
        <b>UNKNOWN</b> means the run predates checkpointing — a folder exists but no
        <span class="mono">run_status.json</span>. <b>source: log_export</b> means it was
        recovered from an app log download rather than written by the run itself.
        {"<b style='color:var(--warn)'>" + str(_n_orphan) + " run(s) have no round</b> — "
         "<span class='mono'>python pipeline/watch_execution.py --reconcile</span>"
         if _n_orphan else "Every run is attributed to a round."}
      </div>
    </div></div>
    """)
    return


@app.cell
def _(mo, rounds):
    picker = mo.ui.dropdown(
        options={f"{rid} — {rec.get('title', '')}": rid for rid, rec in sorted(rounds.items())},
        label="Inspect a round",
        value=next(iter(sorted(f"{rid} — {rec.get('title','')}" for rid, rec in rounds.items())), None),
    )
    picker
    return (picker,)


@app.cell
def _(all_issues, label_value, mo, picker, rounds):
    mo.stop(not picker.value, mo.md("Pick a round above."))
    round_id = picker.value
    round_rec = rounds[round_id]
    children = [
        v for v in all_issues.values()
        if v.get("id", "").startswith(f"{round_id}.")
    ]
    execs = [c for c in children if (c.get("metadata") or {}).get("execution_id")]
    events = sorted(
        (c for c in children if c.get("issue_type") == "event"),
        key=lambda c: c.get("created_at", ""),
    )
    stage = label_value(round_rec, "stage:")
    assay = label_value(round_rec, "assay:")
    return assay, events, execs, round_id, round_rec, stage


@app.cell
def _(assay, events, execs, mo, round_id, round_rec, stage):
    # The round's own lifecycle as a graph — stage transitions in the order beads
    # recorded them, with the physical executions hanging off it. This is the
    # provenance claim made visual: what was intended, what ran, how it ended.
    _STAGE_FILL = {
        "planned": "#2a78d6", "simulated": "#1baf7a", "approved": "#0ca30c",
        "running": "#eda100", "decided": "#4a3aa7", "deviated": "#d03b3b",
    }
    _seen, _chain = [], []
    for e in events:
        _t = (e.get("title") or "")
        if "stage →" in _t:
            _s = _t.split("stage →")[-1].strip()
            if not _chain or _chain[-1] != _s:
                _chain.append(_s)
    if not _chain:
        _chain = [stage or "planned"]

    _lines = ["graph LR", f'  R["{round_id}<br/><i>{assay}</i>"]']
    _prev = "R"
    for _i, _s in enumerate(_chain):
        _nid = f"S{_i}"
        _lines.append(f'  {_nid}["{_s}"]')
        _lines.append(f"  {_prev} --> {_nid}")
        _lines.append(f"  style {_nid} fill:{_STAGE_FILL.get(_s, '#898781')},color:#fff,stroke:none")
        _prev = _nid
    for _i, _c in enumerate(execs):
        _eid = (_c.get("metadata") or {}).get("execution_id", "")
        _lines.append(f'  E{_i}["run<br/>{_eid.replace("exec_", "")[:34]}"]')
        _lines.append(f"  {_prev} -.-> E{_i}")
        _lines.append(f"  style E{_i} fill:#f9f9f7,stroke:#c3c2b7,color:#0b0b0b")
    _lines.append("  style R fill:#0b0b0b,color:#fff,stroke:none")

    mo.vstack([
        mo.md(f"### {round_id} · `{assay}` · stage `{stage}`"),
        mo.mermaid("\n".join(_lines)),
        mo.md(f"_{len(execs)} linked execution(s), {len(events)} recorded state change(s)._"),
        mo.md("**Notes**\n\n" + "\n".join(
            f"- {n}" for n in (round_rec.get("notes") or "").splitlines() if n.strip()
        ) if round_rec.get("notes") else ""),
    ])
    return


@app.cell
def _(CSS, INPUTS_DIR, PROJECT_ROOT, json, mo, round_id, watch):
    # Plate map. Identity colouring (which role a well plays), not magnitude — a
    # well carries three different volumes, so one hue per measure would be a lie.
    # Volumes ride in the hover title instead.
    def _load_layout(rid):
        p = INPUTS_DIR / f"{rid}.json"
        if p.exists():
            return json.loads(p.read_text()), f"inputs/{rid}.json (planned)"
        for _r in watch.discover_executions():
            for _f in _r["folders"]:
                q = PROJECT_ROOT / "data" / "logs" / _r["execution_id"] / _f / "run_inputs.json"
                if q.exists():
                    return json.loads(q.read_text()), f"data/logs/{_r['execution_id'][:26]}…"
        return None, None

    _vals, _src = _load_layout(round_id)
    _wells = {}
    if _vals:
        for _i in range(1, 4):
            for _j in range(1, 4):
                _w = _vals.get(f"pt_e{_i}s{_j}_well")
                if _w:
                    _wells[_w] = ("grid", f"e{_i}s{_j}",
                                  f"enzyme {_vals.get(f'pt_e{_i}s{_j}_enzyme_vol_ul')} µL · "
                                  f"substrate {_vals.get(f'pt_e{_i}s{_j}_substrate_vol_ul')} µL · "
                                  f"buffer {_vals.get(f'pt_e{_i}s{_j}_buffer_vol_ul')} µL")
        for _b, _lab in (("blank_e", "blank E"), ("blank_s", "blank S")):
            _w = _vals.get(f"{_b}_well")
            if _w:
                _wells[_w] = ("blank", _lab,
                              f"{_vals.get(f'{_b}_vol_ul')} µL + buffer "
                              f"{_vals.get(f'{_b}_buffer_vol_ul')} µL")
        for _d in range(1, 13):
            _w = _vals.get(f"dose{_d}_well")
            if _w:
                _wells[_w] = ("dose", f"d{_d}",
                              f"compound {_vals.get(f'dose{_d}_compound_vol_ul')} µL · "
                              f"nitrocefin {_vals.get(f'dose{_d}_nitrocefin_vol_ul')} µL")

    _FILL = {"grid": "var(--s1)", "blank": "var(--s3)", "dose": "var(--s2)"}
    _cells = []
    for _r_i, _row in enumerate("ABCDEFGH"):
        for _c in range(1, 13):
            _w = f"{_row}{_c}"
            _role = _wells.get(_w)
            if _role:
                _kind, _lab, _detail = _role
                _cells.append(
                    f'<div title="{_w} — {_lab}\n{_detail}" style="background:{_FILL[_kind]};'
                    f'color:#fff;border-radius:5px;display:flex;align-items:center;'
                    f'justify-content:center;font-size:8.5px;font-weight:700;height:26px;'
                    f'font-family:ui-monospace,Menlo,monospace">{_lab}</div>')
            else:
                _cells.append(
                    f'<div title="{_w} — unused" style="background:transparent;'
                    f'border:1px solid var(--grid);border-radius:5px;height:26px"></div>')

    _hdr = "".join(f'<div style="font-size:9px;color:var(--muted);text-align:center;'
                   f'font-family:ui-monospace,Menlo,monospace">{c}</div>' for c in range(1, 13))
    _rowlabels = "".join(f'<div style="font-size:9px;color:var(--muted);display:flex;'
                         f'align-items:center;font-family:ui-monospace,Menlo,monospace">{r}</div>'
                         for r in "ABCDEFGH")
    _grid_cells = "".join(_cells)

    mo.Html(CSS + (f"""
    <div class="viz"><div class="card">
      <h3>Plate map — {round_id}</h3>
      <div style="display:grid;grid-template-columns:14px repeat(12,1fr);gap:3px;max-width:640px">
        <div></div>{_hdr}
      </div>
      <div style="display:grid;grid-template-columns:14px 1fr;gap:3px;max-width:640px;margin-top:3px">
        <div style="display:grid;grid-template-rows:repeat(8,26px);gap:3px">{_rowlabels}</div>
        <div style="display:grid;grid-template-columns:repeat(12,1fr);
                    grid-template-rows:repeat(8,26px);gap:3px">{_grid_cells}</div>
      </div>
      <div class="legend">
        <span><span class="swatch" style="background:var(--s1)"></span>grid point</span>
        <span><span class="swatch" style="background:var(--s3)"></span>blank</span>
        <span><span class="swatch" style="background:var(--s2)"></span>dose position</span>
        <span><span class="swatch" style="background:transparent;border:1px solid var(--axis)"></span>unused</span>
      </div>
      <div class="note">Hover a well for its volumes. Source: <span class="mono">{_src}</span>.
      Colour is the well's <i>role</i>, not a volume — each well carries three different
      volumes, so a single hue per well could only encode one of them.</div>
    </div></div>
    """ if _wells else """
    <div class="viz"><div class="card"><h3>Plate map</h3>
    <div class="note">No layout for this round — it has no input preset, and no linked
    run recorded its inputs. Runs recovered from app log exports carry step boundaries
    only, so their plate layout is genuinely unknown rather than blank.</div>
    </div></div>"""))
    return


@app.cell
def _(RESULTS_DIR, json, mo, round_id):
    result_path = RESULTS_DIR / f"{round_id}.json"
    mo.stop(not result_path.exists(),
            mo.md("_No analysis results for this round yet (Analyze hasn't run)._"))
    results = json.loads(result_path.read_text())
    return (results,)


@app.cell
def _(CSS, mo, results, round_id):
    def _inhibitor_curve_html(results):
        # FORM: line (fitted 4PL model) + dot (observed response) on one log-dose
        # axis — one compound per round, so one series: no legend needed, identity
        # is named in the title above the chart instead. IC50 is a reference line,
        # not data, so it stays in ink/muted tokens rather than a categorical hue.
        import math

        fit = results.get("fit", {})
        doses = results["doses_ul"]
        responses = results["response"]
        has_fit = "ic50" in fit

        log_doses = [math.log10(d) if d > 0 else math.log10(1e-6) for d in doses]
        lo, hi = min(log_doses), max(log_doses)
        pad = (hi - lo) * 0.15 or 0.5
        lo, hi = lo - pad, hi + pad

        y_vals = list(responses) + ([fit["bottom"], fit["top"]] if has_fit else [])
        y_lo, y_hi = min(y_vals), max(y_vals)
        y_pad = (y_hi - y_lo) * 0.15 or 0.05
        y_lo, y_hi = y_lo - y_pad, y_hi + y_pad

        PAD_L, PAD_R, PAD_T, PAD_B = 52, 16, 26, 34
        W, H = 600, 250
        PW, PH = W - PAD_L - PAD_R, H - PAD_T - PAD_B

        def x_of(logd):
            return PAD_L + (logd - lo) / (hi - lo) * PW

        def y_of(v):
            return PAD_T + (1 - (v - y_lo) / (y_hi - y_lo)) * PH

        _fracs = (0.0, 0.5, 1.0)
        grid = "".join(
            f'<line x1="{PAD_L}" y1="{y_of(y_lo + f * (y_hi - y_lo)):.1f}" '
            f'x2="{W - PAD_R}" y2="{y_of(y_lo + f * (y_hi - y_lo)):.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
            for f in _fracs
        )
        y_ticks = "".join(
            f'<text x="{PAD_L - 6}" y="{y_of(y_lo + f * (y_hi - y_lo)) + 3:.1f}" text-anchor="end" '
            f'class="mono" font-size="9" fill="var(--muted)">{y_lo + f * (y_hi - y_lo):.3f}</text>'
            for f in _fracs
        )

        curve = ""
        if has_fit:
            pts = []
            for k in range(61):
                logd = lo + (hi - lo) * k / 60
                d = 10 ** logd
                v = fit["bottom"] + (fit["top"] - fit["bottom"]) / (1 + (d / fit["ic50"]) ** fit["hill_slope"])
                pts.append(f"{x_of(logd):.1f},{y_of(v):.1f}")
            curve = f'<path d="M {" L ".join(pts)}" fill="none" stroke="var(--s1)" stroke-width="2"/>'

        ic50_line = ""
        if has_fit and lo <= math.log10(fit["ic50"]) <= hi:
            xi = x_of(math.log10(fit["ic50"]))
            ic50_line = (
                f'<line x1="{xi:.1f}" y1="{PAD_T}" x2="{xi:.1f}" y2="{H - PAD_B}" '
                f'stroke="var(--ink-2)" stroke-width="1.5" stroke-dasharray="4,3"/>'
                f'<text x="{xi:.1f}" y="{PAD_T - 8}" text-anchor="middle" class="mono" '
                f'font-size="9.5" fill="var(--ink-2)">IC50 {fit["ic50"]:.3g}</text>'
            )

        points = "".join(
            f'<circle cx="{x_of(ld):.1f}" cy="{y_of(r):.1f}" r="5" fill="var(--s1)" '
            f'stroke="var(--surface-1)" stroke-width="1.5"><title>{d:.3g} µL -&gt; {r:.4f}</title></circle>'
            for d, r, ld in zip(doses, responses, log_doses)
        )
        x_ticks = "".join(
            f'<text x="{x_of(ld):.1f}" y="{H - PAD_B + 13:.1f}" text-anchor="middle" class="mono" '
            f'font-size="8" fill="var(--muted)">{d:.2g}</text>'
            for d, ld in zip(doses, log_doses)
        )

        svg = f"""
        <svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;max-width:640px">
          {grid}
          <line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - PAD_R}" y2="{H - PAD_B}" stroke="var(--axis)" stroke-width="1"/>
          <line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{H - PAD_B}" stroke="var(--axis)" stroke-width="1"/>
          {ic50_line}
          {curve}
          {points}
          {y_ticks}
          {x_ticks}
          <text x="{(PAD_L + W - PAD_R) / 2:.1f}" y="{H - 4}" text-anchor="middle" class="mono"
                font-size="9" fill="var(--muted)">dose (µL, log scale)</text>
        </svg>
        """

        rows = "".join(
            f'<tr><td class="mono">{d:.3g}</td><td class="mono" style="text-align:right">{r:.4f}</td></tr>'
            for d, r in zip(doses, responses)
        )
        table = f"""
        <details style="margin-top:8px">
          <summary style="cursor:pointer;font-size:11px;color:var(--ink-2);
                   font-family:ui-monospace,Menlo,monospace">table view</summary>
          <table class="t" style="margin-top:6px"><thead><tr><th>Dose (µL)</th>
          <th style="text-align:right">Response</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </details>
        """

        if has_fit:
            summary = (
                f'IC50 &asymp; <b>{fit["ic50"]:.3g}</b> µL-equivalent &middot; Hill <b>{fit["hill_slope"]:.2f}</b> '
                f'&middot; R&sup2; <b>{fit.get("r_squared", float("nan")):.3f}</b>'
            )
        else:
            summary = fit.get("note", "fit unavailable")

        return f"""
        <div class="note" style="margin-bottom:6px">{summary} &mdash;
        <span class="mono">{results.get('compound_id', '')}</span></div>
        {svg}
        {table}
        """

    _assay = ("raw_kinetic_export" if results.get("kind") == "raw_kinetic_export"
              else "inhibitor" if "fit" in results and "doses_ul" in results
              else "kinetics" if "fits" in results else "cfps_expression")

    if _assay == "raw_kinetic_export":
        _rows = "".join(
            f'<tr><td class="mono">{w}</td>'
            f'<td class="mono" style="text-align:right">{v["initial_rate"]:.5f}</td>'
            f'<td class="mono" style="text-align:right;color:var(--ink-2)">{v["n_timepoints"]}</td></tr>'
            for w, v in sorted(results["well_rates"].items())
        )
        body = f"""
        <table class="t"><thead><tr><th>Well</th>
        <th style="text-align:right">Initial rate (A490/min)</th>
        <th style="text-align:right">Timepoints</th></tr></thead>
        <tbody>{_rows}</tbody></table>
        <div class="note">No input preset for this round, so no enzyme/substrate condition is
        known per well — this is the observed rate straight off the Gen5 kinetic export
        (execution <span class="mono">{results.get('execution_id')}</span>), not a fit.</div>"""
    elif _assay == "kinetics":
        _rows = "".join(
            f'<tr><td class="mono">{k}</td>'
            f'<td class="mono" style="text-align:right">{v.get("vmax", float("nan")):.5f}</td>'
            f'<td class="mono" style="text-align:right">{v.get("km", float("nan")):.4f}</td></tr>'
            for k, v in results["fits"].items()
        )
        body = f"""
        <table class="t"><thead><tr><th>Enzyme level</th>
        <th style="text-align:right">Vmax</th><th style="text-align:right">Km</th></tr></thead>
        <tbody>{_rows}</tbody></table>
        <div class="note">Recommendation: nitrocefin level
        <b>{results.get('recommended_nitrocefin_level')}</b>, endpoint
        <b>{results.get('recommended_endpoint_minutes')} min</b>
        (best fit <span class="mono">{results.get('best_fit')}</span>).</div>"""
    elif _assay == "inhibitor":
        body = _inhibitor_curve_html(results)
    else:
        _go = results.get("go")
        body = (f'<div style="font-size:22px;font-weight:800;'
                f'color:{"var(--good)" if _go else "var(--critical)"}">'
                f'{"GO" if _go else "NO-GO"}</div>'
                f'<div class="note">positive <span class="mono">{results.get("pos_mean")}</span> · '
                f'negative <span class="mono">{results.get("neg_mean")}</span> · '
                f'sample <span class="mono">{results.get("sample_mean")}</span></div>')

    if _assay in ("kinetics", "raw_kinetic_export"):
        _is_real = True
    else:
        _is_real = results.get("data_source") == "real_export"
    _provenance = (
        '<div class="note"><b>Real data.</b> Parsed from a Gen5 PDF export '
        '(<span class="mono">parse_gen5_export</span> in '
        '<span class="mono">analyze_agent.py</span>).</div>'
        if _is_real else
        '<div class="note"><b>Synthetic data.</b> No Gen5 export was found for this execution yet — '
        '<span class="mono">parse_gen5_export</span>\'s stub fallback filled in realistically shaped '
        'numbers, not measurements.</div>'
    )
    mo.Html(CSS + f"""<div class="viz"><div class="card">
      <h3>Analysis — {round_id}</h3>{body}
      {_provenance}
    </div></div>""")
    return


if __name__ == "__main__":
    app.run()
