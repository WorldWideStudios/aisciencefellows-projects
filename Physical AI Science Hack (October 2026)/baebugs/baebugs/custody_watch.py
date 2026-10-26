"""Real-time chain-of-custody watcher + live dashboard.

Every cycle re-verifies the custody graph and classifies each check OK / WARN / DRIFT / BREAK:
  mmr        every *mmr.jsonl: each leaf == sha256(record), each stored root recomputes, and the log
             is APPEND-ONLY: the root over the first n leaves still equals the root seen when the
             log had n leaves (a rewrite or truncation is a BREAK)
  frozen     frozen truths / protocols / preregistrations: sha256 never changes after first sight;
             protocol shas are also cross-checked against the shas recorded in the impact MMR
  upstream   BioKEA / hardware repo mirrors still match their pins (BREAK); upstream moved (DRIFT)
  datasets   members used by frozen protocols: file count + bytes vs manifest every cycle, and a
             rotating sha256 sample of files vs the pointer manifest (BREAK on mismatch)
  git        unpushed commits / dirty tracked files in the repo (WARN)
State changes are written to a hash-chained event log (each event hashes the previous one), so the
watcher's own record is tamper-evident. A new BREAK is surfaced immediately: dashboard banner via
server-sent events, a macOS notification, and a line in the event log.

  python -m baebugs.custody_watch --repo /Users/byron/Projects/baebugs --port 8790
Dashboard: http://<host>:8790/   (status JSON at /status.json, live stream at /events)
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .mmr import MMR, MMRLog

FROZEN_GLOBS = ["daisy/TRUTH-*.json", "daisy/DAISY-BB-*.json", "daisy/DAISY-BB-*.md", "daisy/*prereg*.md"]
LEVELS = {"OK": 0, "WARN": 1, "DRIFT": 1, "BREAK": 2}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def fsha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


class Watcher:
    def __init__(self, repo, state_dir=None, datasets_json=None, sample=12, notify=True):
        self.repo = Path(repo)
        self.state_dir = Path(state_dir or self.repo / ".custody_watch"); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_f = self.state_dir / "state.json"; self.events_f = self.state_dir / "events.jsonl"
        self.state = json.loads(self.state_f.read_text()) if self.state_f.exists() else {"mmr": {}, "frozen": {}}
        self.datasets_json = Path(datasets_json) if datasets_json else None
        self.sample, self.notify = sample, notify
        self.checks, self.last_cycle, self.cycle_n = {}, None, 0
        self.listeners, self.lock = [], threading.Lock()
        self.prev_event = self._last_event_hash()

    # ---------------------------------------------------------------- checks
    def check_mmr(self):
        out = {}
        for f in sorted(self.repo.glob("daisy/*mmr.jsonl")):
            key = f"mmr:{f.name}"
            try:
                log = MMRLog(f)
            except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
                out[key] = ("BREAK", f"unreadable: {e}"); continue
            ok, bad = log.verify()
            if not ok:
                out[key] = ("BREAK", f"leaf/root mismatch at index {bad}"); continue
            n, root = len(log.records), log.mmr.root
            seen = self.state["mmr"].get(f.name)
            if seen:
                if n < seen["n"]:
                    out[key] = ("BREAK", f"log truncated: {n} < {seen['n']} leaves"); continue
                prefix = MMR([r["leaf"] for r in log.records[:seen["n"]]]).root if seen["n"] else None
                if prefix != seen["root"]:
                    out[key] = ("BREAK", f"history rewritten: root of first {seen['n']} leaves changed"); continue
            self.state["mmr"][f.name] = {"n": n, "root": root}
            out[key] = ("OK", f"{n} leaves, append-only, root {root[:12]}")
        return out

    def check_frozen(self):
        out, recorded = {}, {}
        imp = self.repo / "daisy/impact_mmr.jsonl"
        if imp.exists():
            for r in MMRLog(imp).records:
                x = r["record"]
                if x.get("type") == "protocol_frozen" and x.get("sha256"):
                    recorded[x["protocol"]] = x["sha256"]
        files = sorted({p for g in FROZEN_GLOBS for p in self.repo.glob(g)})
        for p in files:
            rel = str(p.relative_to(self.repo)); s = fsha(p); key = f"frozen:{rel}"
            first = self.state["frozen"].setdefault(rel, s)
            pid = p.stem if p.suffix == ".json" else None
            if s != first:
                out[key] = ("BREAK", f"frozen file changed: {first[:12]} -> {s[:12]}")
            elif pid in recorded and recorded[pid] != s:
                out[key] = ("BREAK", f"sha {s[:12]} != MMR-recorded {recorded[pid][:12]}")
            else:
                out[key] = ("OK", f"sha {s[:12]}" + (" = MMR record" if pid in recorded else ""))
        for rel in set(self.state["frozen"]) - {str(p.relative_to(self.repo)) for p in files}:
            out[f"frozen:{rel}"] = ("BREAK", "frozen file deleted")
        return out

    def check_upstream(self, remote=False):
        from .upstream import check, remote_drift
        t = self.repo / "daisy/upstream.json"
        if not t.exists():
            return {"upstream:pins": ("WARN", "no upstream pins yet (python -m baebugs.upstream pin)")}
        out = {}
        for name, p in json.loads(t.read_text()).items():
            c = check(p); out[f"upstream:{name}"] = (c["level"], c["reason"])
            if remote and c["level"] == "OK":
                d = remote_drift(p)
                if d["level"] != "OK":
                    out[f"upstream:{name}"] = (d["level"], d["reason"])
        return out

    def check_datasets(self):
        if not self.datasets_json or not self.datasets_json.exists():
            return {}
        s = json.loads(self.datasets_json.read_text()); mdir = self.datasets_json.parent / "manifests"
        used = set()
        for pj in self.repo.glob("daisy/DAISY-BB-*.json"):
            try:
                used |= set(json.loads(pj.read_text()).get("roots", {}))
            except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
                pass
        out = {}
        for name in sorted(used):
            rec = s["datasets"].get(name); mf = mdir / f"{name}.jsonl"; key = f"dataset:{name}"
            if not rec or not mf.exists():
                out[key] = ("WARN", "no manifest on this host"); continue
            base = Path(rec["path"]); leaves = [json.loads(l) for l in mf.read_text().splitlines() if l.strip()]
            missing = [l["path"] for l in leaves if not (base / l["path"]).is_file()]
            if missing:
                out[key] = ("BREAK", f"{len(missing)} files missing, e.g. {missing[0]}"); continue
            wrong_size = [l["path"] for l in leaves if (base / l["path"]).stat().st_size != l["bytes"]]
            if wrong_size:
                out[key] = ("BREAK", f"{len(wrong_size)} files changed size, e.g. {wrong_size[0]}"); continue
            rng = random.Random(f"{name}:{self.cycle_n}")
            bad = [l["path"] for l in rng.sample(leaves, min(self.sample, len(leaves))) if fsha(base / l["path"]) != l["sha256"]]
            out[key] = (("BREAK", f"sha256 mismatch: {bad[0]}") if bad else
                        ("OK", f"{len(leaves)} files present, sizes match, {min(self.sample, len(leaves))} re-hashed"))
        return out

    def check_resolvable(self):
        """graph invariant: every hash the graph references resolves to stored bytes (weights etc.)"""
        from .resolve import Store, dangling
        roots = [str(self.repo)]
        if self.datasets_json:
            roots += [str(self.datasets_json.parent)] + [str(r) for r in [self.datasets_json.parent.parent / "runs"] if r.exists()]
        store = Store(roots, cache=self.state_dir / "store_index.json").build()
        d = dangling(self.repo, store)
        if not d:
            return {"resolve:graph": ("OK", f"every referenced hash resolves ({len(store.index)} objects indexed)")}
        return {f"resolve:{x['sha'][:12]}": ("BREAK", (f"{x['kind']} referenced by {', '.join(x['contexts'])} "
                                                          f"does not resolve to stored bytes")) for x in d}

    def check_git(self):
        try:
            dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=self.repo,
                                   capture_output=True, text=True, check=False).stdout.strip()
            ahead = subprocess.run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=self.repo,
                                   capture_output=True, text=True, check=False).stdout.strip() or "0"
            head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.repo, capture_output=True, text=True, check=False).stdout.strip()
        except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            return {"git": ("WARN", str(e))}
        if dirty:
            return {"git": ("WARN", f"tracked files modified at {head}: {len(dirty.splitlines())}")}
        if ahead != "0":
            return {"git": ("WARN", f"{ahead} commits not pushed (HEAD {head})")}
        return {"git": ("OK", f"clean, pushed, HEAD {head}")}

    # ---------------------------------------------------------------- cycle
    def cycle(self, remote=False):
        self.cycle_n += 1
        new = {}
        for fn in (self.check_mmr, self.check_frozen, lambda: self.check_upstream(remote), self.check_datasets,
                   self.check_resolvable, self.check_git):
            try:
                new.update(fn())
            except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
                new[f"watcher:{getattr(fn, '__name__', 'check')}"] = ("WARN", f"check crashed: {type(e).__name__}: {e}")
        changed = []
        for k, (lvl, why) in new.items():
            old = self.checks.get(k)
            if not old or old["level"] != lvl:
                changed.append(self._event(k, old and old["level"], lvl, why))
            self.checks[k] = {"level": lvl, "reason": why, "since": (old or {}).get("since") if old and old["level"] == lvl
                              else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        for k in set(self.checks) - set(new):
            changed.append(self._event(k, self.checks[k]["level"], "BREAK", "check disappeared"))
            self.checks[k] = {"level": "BREAK", "reason": "check disappeared", "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.last_cycle = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.state_f.write_text(json.dumps(self.state, indent=1))
        snap = self.status()
        for q in list(self.listeners):
            q.append(snap)
        breaks = [e for e in changed if e["to"] == "BREAK"]
        if breaks and self.notify:
            self._notify(breaks)
        return snap, changed

    def _event(self, key, frm, to, why):
        e = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "check": key, "from": frm, "to": to,
             "reason": why, "prev": self.prev_event}
        e["hash"] = H(e); self.prev_event = e["hash"]
        with self.events_f.open("a") as f:
            f.write(json.dumps(e) + "\n")
        return e

    def _last_event_hash(self):
        if not self.events_f.exists():
            return None
        lines = [l for l in self.events_f.read_text().splitlines() if l.strip()]
        return json.loads(lines[-1])["hash"] if lines else None

    def verify_events(self):
        prev = None
        for i, l in enumerate(l for l in self.events_f.read_text().splitlines() if l.strip()):
            e = json.loads(l); h = e.pop("hash")
            if e["prev"] != prev or H(e) != h:
                return False, i
            prev = h
        return True, None

    def _notify(self, breaks):
        msg = f"{len(breaks)} custody BREAK: " + "; ".join(f"{b['check']}: {b['reason']}" for b in breaks[:3])
        try:
            subprocess.run(["osascript", "-e", f'display notification {json.dumps(msg[:220])} with title "baebugs custody"'],
                           timeout=5, capture_output=True, check=False)
        except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
            pass

    def status(self):
        worst = max((LEVELS[c["level"]] for c in self.checks.values()), default=0)
        ok_chain = self.verify_events()[0] if self.events_f.exists() else True
        recent = [json.loads(l) for l in self.events_f.read_text().splitlines()[-40:]] if self.events_f.exists() else []
        return {"overall": ["OK", "WARN", "BREAK"][worst] if ok_chain else "BREAK", "event_chain_ok": ok_chain,
                "last_cycle": self.last_cycle, "cycle": self.cycle_n, "checks": self.checks, "recent_events": recent[::-1]}


# ---------------------------------------------------------------- dashboard
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Custody Watch</title><style>
:root{--bg:#f7f7f4;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--line:#e3e3dd;--ok:#2e7d4f;--warn:#a86b00;--brk:#b3261e;--drift:#4a5fb0}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#eceae4;--mut:#9b9a94;--card:#1e1e1c;--line:#33332f;--ok:#5cc28a;--warn:#e0a63a;--brk:#ff6b5e;--drift:#8fa2ff}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
#banner{border-radius:10px;padding:14px 16px;font-weight:600;margin-bottom:14px;color:#fff}
.OK{background:var(--ok)}.WARN{background:var(--warn)}.BREAK{background:var(--brk)}.DRIFT{background:var(--drift)}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:20px 0 8px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
td{padding:7px 10px;border-top:1px solid var(--line);vertical-align:top;word-break:break-word}
.pill{display:inline-block;min-width:54px;text-align:center;border-radius:99px;color:#fff;font-size:12px;font-weight:700;padding:2px 8px}
.k{font-family:ui-monospace,monospace;font-size:13px}.m{color:var(--mut);font-size:13px}
</style></head><body><main>
<div id="banner" class="WARN">connecting…</div>
<div class="m" id="meta"></div>
<h2>Recent state changes (hash-chained)</h2><table id="ev"></table>
<h2>Checks</h2><table id="ck"></table>
</main><script>
const lv={BREAK:0,DRIFT:1,WARN:2,OK:3};
function esc(s){return String(s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function render(s){
  const n=Object.values(s.checks).filter(c=>c.level==="BREAK").length;
  const b=document.getElementById("banner");b.className=s.overall;
  b.textContent=s.overall==="BREAK"?`CHAIN OF CUSTODY BROKEN — ${n} check(s)`+(s.event_chain_ok?"":" · watcher event log tampered"):
    s.overall==="WARN"?"Custody intact · warnings present":"Custody intact";
  document.getElementById("meta").textContent=`cycle ${s.cycle} · last check ${s.last_cycle} UTC · ${Object.keys(s.checks).length} checks`;
  const rows=Object.entries(s.checks).sort((a,b)=>lv[a[1].level]-lv[b[1].level]||a[0].localeCompare(b[0]));
  document.getElementById("ck").innerHTML=rows.map(([k,c])=>`<tr><td><span class="pill ${c.level}">${c.level}</span></td><td class="k">${esc(k)}</td><td>${esc(c.reason)}<div class="m">since ${esc(c.since)}</div></td></tr>`).join("");
  document.getElementById("ev").innerHTML=(s.recent_events||[]).slice(0,15).map(e=>`<tr><td class="m">${esc(e.t)}</td><td class="k">${esc(e.check)}</td><td>${esc(e.from||"—")} → <span class="pill ${e.to}">${e.to}</span> ${esc(e.reason)}</td><td class="k m">${esc(e.hash.slice(0,10))}</td></tr>`).join("")||'<tr><td class="m">no changes yet</td></tr>';
  if(s.overall==="BREAK"&&document.hidden&&window.Notification&&Notification.permission==="granted")new Notification("baebugs custody BREAK");
}
fetch("status.json").then(r=>r.json()).then(render);
const es=new EventSource("events");es.onmessage=m=>render(JSON.parse(m.data));
es.onerror=()=>{const b=document.getElementById("banner");b.className="WARN";b.textContent="watcher unreachable — status unknown"};
if(window.Notification&&Notification.permission==="default")Notification.requestPermission();
</script></body></html>"""


def make_server(w, host, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = PAGE.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/status.json":
                body = json.dumps(w.status()).encode(); self.send_response(200)
                self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
            elif self.path == "/events":
                self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache"); self.end_headers()
                q = []; w.listeners.append(q)
                try:
                    self.wfile.write(f"data: {json.dumps(w.status())}\n\n".encode()); self.wfile.flush()
                    while True:
                        if q:
                            self.wfile.write(f"data: {json.dumps(q.pop(0))}\n\n".encode()); self.wfile.flush()
                        else:
                            time.sleep(0.5); self.wfile.write(b": ping\n\n"); self.wfile.flush()
                except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
                    pass
                finally:
                    w.listeners.remove(q)
            else:
                self.send_response(404); self.end_headers()
    return ThreadingHTTPServer((host, port), Handler)          # binds now: a taken port fails loudly


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-custody-watch")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--datasets-json", default="/Volumes/magicBLACKbox/baebugs/daisy/datasets.json")
    ap.add_argument("--interval", type=float, default=15.0, help="seconds between local checks")
    ap.add_argument("--remote-every", type=int, default=20, help="check upstream HEADs every N cycles")
    ap.add_argument("--host", default="0.0.0.0"); ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    w = Watcher(a.repo, datasets_json=a.datasets_json)
    if a.once:
        s, ch = w.cycle(remote=True); print(json.dumps({"overall": s["overall"], "changes": len(ch)}, indent=1))
        for k, c in sorted(s["checks"].items()):
            print(f"{c['level']:6s} {k}: {c['reason']}")
        return
    srv = make_server(w, a.host, a.port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"custody watch on http://{a.host}:{a.port}/", flush=True)
    while True:
        w.cycle(remote=(w.cycle_n % a.remote_every == 0)); time.sleep(a.interval)


if __name__ == "__main__":
    main()
