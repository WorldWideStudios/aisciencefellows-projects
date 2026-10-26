"""Slice a part headlessly with Bambu Studio: print time and filament before anyone prints.

Run:  ..\\.venv\\Scripts\\python.exe slice.py hole_gauge [--printer P1S]

Writes out/slice/<name>.gcode.3mf and prints the estimate. Use it to compare
iterations. Send the real print from the Bambu Studio app, where you pick the
printer and build plate that are actually on the bench.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"  # same as cadkit.OUT; no cadquery import, so it runs under SAC
STUDIO = Path(r"C:\Program Files\Bambu Studio")
PROFILES = STUDIO / "resources" / "profiles" / "BBL"
PRINTERS = {  # each machine preset names its own default process and filament
    "X1C": "Bambu Lab X1 Carbon 0.4 nozzle",
    "P1S": "Bambu Lab P1S 0.4 nozzle",
    "P2S": "Bambu Lab P2S 0.4 nozzle",
    "A1": "Bambu Lab A1 0.4 nozzle",
    "A1M": "Bambu Lab A1 mini 0.4 nozzle",
}


def flat(kind, name):
    """System presets only store overrides; the CLI needs the whole inherits chain merged."""
    data = json.loads((PROFILES / kind / f"{name}.json").read_text(encoding="utf-8"))
    parent = data.pop("inherits", None)
    return {**flat(kind, parent), **data} if parent else data


def slice_stls(names, out_name, printer="P1S"):
    """Slice out/<name>.stl for every name onto one plate (arranged when there are several);
    returns minutes, grams and the .gcode.3mf path."""
    machine = flat("machine", PRINTERS[printer])
    work = OUT / "slice"
    work.mkdir(parents=True, exist_ok=True)
    presets = {}
    for kind, data in (("machine", machine),
                       ("process", flat("process", machine["default_print_profile"])),
                       ("filament", flat("filament", machine["default_filament_profile"][0]))):
        presets[kind] = work / f"{kind}.json"
        presets[kind].write_text(json.dumps(data), encoding="utf-8")
    (work / "result.json").unlink(missing_ok=True)
    subprocess.run([str(STUDIO / "bambu-studio.exe"),
                    "--load-settings", f"{presets['machine']};{presets['process']}",
                    "--load-filaments", str(presets["filament"]),
                    *(["--arrange", "1"] if len(names) > 1 else []),
                    "--slice", "0", "--outputdir", str(work),
                    "--export-3mf", f"{out_name}.gcode.3mf", *(str(OUT / f"{n}.stl") for n in names)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = json.loads((work / "result.json").read_text())
    if result["return_code"] != 0 or len(result["sliced_plates"]) != 1:
        raise RuntimeError(f"slice {out_name} failed: {result['error_string']} "
                           f"({len(result.get('sliced_plates', []))} plates)")
    plate = result["sliced_plates"][0]
    head = (work / "plate_1.gcode").read_text(errors="replace")[:20000]
    return {"minutes": plate["total_predication"] / 60,
            "grams": float(re.search(r"total filament weight \[g\] : ([\d.]+)", head).group(1)),
            "path": work / f"{out_name}.gcode.3mf"}


def slice_part(name, printer="P1S"):
    """Slice out/<name>.stl on its own: the per-part estimate."""
    return slice_stls([name], name, printer)


def slice_plate(names, out_name, printer="P1S"):
    """Arrange several parts on one plate and slice it: the file to send to the printer."""
    return slice_stls(names, out_name, printer)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="part name in out/, e.g. hole_gauge")
    ap.add_argument("--printer", default="P1S", choices=PRINTERS)
    a = ap.parse_args()
    r = slice_part(a.name, a.printer)
    print(f"{a.name} on {a.printer}: {r['minutes']:.0f} min, {r['grams']:.1f} g PLA -> {r['path']}")


if __name__ == "__main__":
    main()
