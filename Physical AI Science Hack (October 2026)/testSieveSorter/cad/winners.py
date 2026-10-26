"""Build, preview and slice the design optimizer's winners, then write the print plan.

Run on Windows from this folder:  ..\\.venv\\Scripts\\python.exe winners.py [..\\sim\\opt\\winners.json] [--no-build]
1. build_winners.py in the WSL venv (cadquery is blocked on Windows by Smart App Control): every part as
   out/win<rank>_<part>.stl/.step/.png plus checks, and a preview of each winner's tower;
2. slice.py here with Bambu Studio (P1S by default): time and grams per part, and one arranged plate per
   winner (out/slice/win<rank>_plate.gcode.3mf), the file to send to the printer;
3. sim/opt/print_plan.md (print_plan_<study>.md for other studies): one table per winner, then the breaker
   layer(s) from breaker_layer.py (out/breaker_build.json), sliced, to print after the winner plate.
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from slice import OUT, slice_part, slice_plate

HERE = Path(__file__).resolve().parent
OPT = HERE.parent / "sim" / "opt"
WSL_PY = "~/venvs/sieve/bin/python"
KEEP = "<!-- hand-written from here on: winners.py keeps it -->"


def wsl_path(p: Path) -> str:
    p = p.resolve()
    return f"/mnt/{p.drive[0].lower()}{p.as_posix()[2:]}"


def build(winners: Path):
    cmd = f"cd '{wsl_path(HERE)}' && {WSL_PY} build_winners.py '{wsl_path(winners)}' 2>&1 | grep -v 'bad X server'"
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-lc", cmd])
    if r.returncode:
        raise SystemExit("winners: the WSL build failed")


def repo_rel(path: str) -> str:
    """WSL or Windows path -> repo-relative when inside the repo."""
    p = path.replace("/mnt/c/", "C:/") if path.startswith("/mnt/c/") else path
    try:
        return Path(p).resolve().relative_to(HERE.parent).as_posix()
    except ValueError:
        return Path(p).as_posix()


def plan_md(built: dict, sliced: dict, plates: dict, printer: str, breakers=()) -> str:
    lines = [f"# Print plan: {built['study']} winners", "",
             f"Built {built['built']} from `{repo_rel(built['source'])}`, "
             f"sliced for the {printer} (Bambu Studio's default process, PLA). Made by `cad/winners.py`.", "",
             f"**Caveat:** {(built.get('caveat') or 'sim ranking only').rstrip('.')}." + (
                 f" The CAD is drawn at the nominal sizes; the sim assumed openings print "
                 f"{built['undersize_mm_assumed']} mm small. Check that against `hole_gauge` before trusting a gate "
                 "size to 0.1 mm." if built.get("undersize_mm_assumed") is not None else ""), ""]
    for w in built["winners"]:
        stroke = w.get("stroke") or {}
        stroke_s = ", ".join(f"{k} {v:g}" if isinstance(v, (int, float)) else f"{k} {v}" for k, v in stroke.items())
        score = (w.get("score") or {}).get("robust")
        lines += [f"## Winner {w['rank']}: {w['family']}", "",
                  f"- Sim spec: `{w['sim_spec']}`" + (f", robust score {score:.3f}" if score is not None else ""),
                  f"- Stroke to set on the Pi: {w.get('stroke_human') or stroke_s or 'n/a'}"
                  + (f" ({stroke_s})" if w.get("stroke_human") and stroke_s else ""),
                  f"- Tower preview: `cad/out/{next((p['name'] for p in w['parts'] if not p['print']), '-')}.png`"]
        if w.get("assembly"):
            lines += ["- Assembly, top first:"] + [f"  - {a}" for a in w["assembly"]]
        lines += ["", "| Part | Time | Filament | Checks |", "|---|---|---|---|"]
        tot_min = tot_g = 0.0
        for p in w["parts"]:
            if not p["print"]:
                continue
            s = sliced.get(p["name"])
            if s is None:
                lines.append(f"| `{p['name']}` | slice failed | | {'ok' if p['checks_ok'] else 'FAILED'} |")
                continue
            tot_min += s["minutes"]
            tot_g += s["grams"]
            lines.append(f"| `{p['name']}` | {s['minutes']:.0f} min | {s['grams']:.1f} g | "
                         f"{'ok' if p['checks_ok'] else 'FAILED'} |")
        lines += [f"| **Total, one of each** | **{tot_min:.0f} min** | **{tot_g:.1f} g** | |", ""]
        plate = plates.get(w["rank"])
        if isinstance(plate, dict):
            lines += [f"**One plate, ready to print:** {plate['minutes']:.0f} min, {plate['grams']:.1f} g, all parts "
                      f"arranged on one {printer} plate: `cad/out/slice/{plate['path'].name}` (local, not committed).", ""]
        elif plate:
            lines += [f"The parts don't slice as one plate ({plate}); print them one by one.", ""]
        if w["flags"]:
            lines += ["Printability flags (also go into `sim/opt/LOG.md` as constraints):", ""]
            lines += [f"- {f}" for f in w["flags"]] + [""]
        else:
            lines += ["No printability flags.", ""]
    for b, s in breakers:
        i = b["info"]
        lines += ["## Breaker layer (prints after the winner plate)", "",
                  f"The clump breaker for the top of the stack (`docs/sessions/clump-breakup.md`): `{i['spec']}`, "
                  "built by `cad/breaker_layer.py`. These sizes are a sensible default, not an optimizer result; the "
                  "optimizer's `malaise` study searches the same parameters, and a winner from it builds the same way.", "",
                  "| Part | Time | Filament | Checks |", "|---|---|---|---|",
                  f"| `{b['name']}` | " + (f"{s['minutes']:.0f} min | {s['grams']:.1f} g" if isinstance(s, dict)
                                          else f"slice failed ({s}) |") + f" | {'ok' if b['checks_ok'] else 'FAILED'} |", "",
                  f"- {i['openings'][0]} x {i['openings'][1]} openings ({i['open_pct_of_box_bottom']:g}% of the box's open "
                  f"bottom), {i['pins']} pins {i['pin_pitch_mm']:g} mm apart, tops {i['pin_top_in_box_mm']:g} mm up the box.",
                  f"- Preview: `cad/out/{b['name']}_preview.png`. Sliced file: `cad/out/slice/{b['name']}.gcode.3mf` "
                  "(local, not committed).",
                  "- " + ("Printability flags: " + "; ".join(i["printability_flags"]) if i["printability_flags"]
                          else "No printability flags."), "",
                  "**Bench demo clump (a suggestion to the team).** Stir rice, quinoa and a few pasta tubes with a "
                  "little sugar water (a water-soluble binder) and some torn leaf bits, press it into a ball about 30 mm "
                  "across and let it set for a few minutes. Put it on the breaker layer, run the shake with the spray "
                  "on, and film it side-on: it should come apart on the pins, the leaf bits should stay on the breaker, "
                  "and the grains should sort on the trays below. The binder dissolves in the spray, standing in for "
                  "the ethanol film. How strong it is next to a real Malaise clump is an assumption.", ""]
    lines += ["Checks: valid single solid, watertight mesh, fits the bed. A tower needs one holder box per level "
              "plus the catch pan; the holder (`frame_holder`) isn't repeated here.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("winners", nargs="?", type=Path, default=OPT / "winners.json")
    ap.add_argument("--no-build", action="store_true", help="reuse out/winners_build*.json and the STLs")
    ap.add_argument("--printer", default="P1S")
    ap.add_argument("--plan", type=Path, help="where to write the plan (default sim/opt/print_plan[_<study>].md)")
    args = ap.parse_args()
    study = json.loads(args.winners.read_text(encoding="utf-8")).get("study", "demo")
    if not args.no_build:
        build(args.winners)
    built = json.loads((OUT / ("winners_build.json" if study == "demo" else f"winners_build_{study}.json"))
                       .read_text(encoding="utf-8"))
    sliced, plates = {}, {}
    for w in built["winners"]:
        names = [p["name"] for p in w["parts"] if p["print"]]
        for n in names:
            try:
                sliced[n] = slice_part(n, args.printer)
                print(f"{n}: {sliced[n]['minutes']:.0f} min, {sliced[n]['grams']:.1f} g")
            except RuntimeError as e:
                print(f"{n}: {e}")
        prefix = f"win{w['rank']}_" if study == "demo" else f"{study}_win{w['rank']}_"
        try:
            plates[w["rank"]] = slice_plate(names, prefix + "plate", args.printer)
            print(f"{prefix}plate: {plates[w['rank']]['minutes']:.0f} min, {plates[w['rank']]['grams']:.1f} g")
        except RuntimeError as e:
            plates[w["rank"]] = str(e)
            print(f"{prefix}plate: {e}")
    breakers = []                  # breaker_layer.py's builds (out/breaker_build.json) print after the winner plate
    if study == "demo" and (OUT / "breaker_build.json").exists():
        for b in json.loads((OUT / "breaker_build.json").read_text(encoding="utf-8")):
            try:
                s = slice_part(b["name"], args.printer)
                print(f"{b['name']}: {s['minutes']:.0f} min, {s['grams']:.1f} g")
            except RuntimeError as e:
                s = str(e)
                print(f"{b['name']}: {e}")
            breakers.append((b, s))
    plan = args.plan or OPT / ("print_plan.md" if study == "demo" else f"print_plan_{study}.md")
    plan.parent.mkdir(parents=True, exist_ok=True)
    old = plan.read_text(encoding="utf-8") if plan.exists() else ""
    kept = old[old.index(KEEP):] if KEEP in old else ""        # the hand-written queue and seesaw parts
    plan.write_text(plan_md(built, sliced, plates, args.printer, breakers) + kept, encoding="utf-8")
    print(f"winners: wrote {plan} ({datetime.now():%H:%M})")


if __name__ == "__main__":
    main()
