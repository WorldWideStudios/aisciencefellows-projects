"""Real-vs-sim side-by-side clip: scale both to one height, hstack, label each half.

Run from sim\\:
  python side_by_side.py --real <phone clip or photo> --sim <sim clip> [-o ../media/demo_side_by_side.mp4]
      [--real-start S] [--sim-start S] [--duration S] [--height 720] [--slow 4 --loops 3 --caption ..]
A photo (.jpg/.png) as --real is held for the whole sim clip.
--slow stretches the real clip; render the sim half at the matching speed (record_view.py --speed 0.25
for --slow 4) so both halves show the same span of physical time. The sim clip is record_view.py's MP4
or a .webm from the replay page's Record button (at 1x, unless it was recorded slowed). Chrome's
MediaRecorder writes full-range pixels into a WebM tagged limited-range, which decodes with the
light greys clipped to white; that is detected from a background pixel and undone. Both halves are
resampled to --fps and the output bitrate is capped so the file stays under --max-mb.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height,color_range:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    dur = j.get("format", {}).get("duration")
    s["duration"] = float(dur) if dur not in (None, "N/A") else None
    return s


STILLS = {".jpg", ".jpeg", ".png"}


def display_size(path: Path) -> tuple[int, int]:
    """Width and height as shown, from a decoded first frame, so a phone clip's display rotation and a
    photo's EXIF orientation are both applied the way ffmpeg applies them below."""
    png = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "image2pipe",
                          "-c:v", "png", "-"], capture_output=True, check=True).stdout
    return int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")     # PNG IHDR


def duration(path: Path) -> float:
    """Container duration, or the last frame's timestamp (MediaRecorder WebMs have no duration)."""
    d = probe(path)["duration"]
    if d:
        return d
    ts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
                         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.split()
    return float(ts[-1]) if ts else 0.0


def mislabeled_full_range(path: Path, start: float) -> bool:
    """True if the clip carries full-range luma but decodes as limited range: the raw Y of the corner (scene
    background, #eef1f5) is above 235. The tags can't be trusted either way: Chrome's VP9 WebM says tv, its
    VP8 WebM says pc at the container level, and ffmpeg's VP8 decoder still hands the frames on as tv."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start}", "-i", str(path), "-frames:v", "1",
                          "-vf", "crop=8:8:8:8", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                         capture_output=True, check=True).stdout
    y = raw[:64]                          # the 8x8 luma plane comes first, unconverted
    return bool(y) and sum(y) / len(y) > 235


def ff_path(p: Path) -> str:
    """A path inside a filtergraph option: forward slashes, drive colon escaped, quoted."""
    return "'" + p.as_posix().replace(":", r"\:") + "'"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--real", type=Path, required=True)
    ap.add_argument("--sim", type=Path, required=True)
    ap.add_argument("-o", "--out", type=Path, default=HERE.parent / "media" / "demo_side_by_side.mp4")
    ap.add_argument("--real-start", type=float, default=0.0, help="s into the real clip where the output starts")
    ap.add_argument("--sim-start", type=float, default=0.0, help="s into the sim clip where the output starts")
    ap.add_argument("--duration", type=float, help="output length, s (default: the shorter clip)")
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--real-label", default="Real BugSorter")
    ap.add_argument("--sim-label", default="MuJoCo sim, uncalibrated")
    ap.add_argument("--slow", type=float, default=1.0,
                    help="play the real clip this many times slower; render the sim with record_view.py --speed 1/SLOW")
    ap.add_argument("--loops", type=int, default=1, help="play the synced pair this many times")
    ap.add_argument("--caption", help=r"text across the bottom, e.g. the playback speed; \n starts a new line")
    ap.add_argument("--max-mb", type=float, default=19.0)
    args = ap.parse_args()

    # span: output seconds of one pass; the real clip is cut to span / slow of its own time, then stretched
    still = args.real.suffix.lower() in STILLS
    span = duration(args.sim) - args.sim_start
    if not still:
        span = min((duration(args.real) - args.real_start) * args.slow, span)
    if args.duration:
        span = min(span, args.duration)
    if span <= 0:
        raise SystemExit("side_by_side: nothing to render (check the start times)")
    h = args.height // 2 * 2
    widths = [round(w * h / hh / 2) * 2 for w, hh in (display_size(args.real), display_size(args.sim))]
    sim_fix = "setparams=range=pc," if mislabeled_full_range(args.sim, args.sim_start) else ""
    total = span * args.loops
    kbps = int(min(8000, args.max_mb * 8e3 * 0.95 / total))     # cap so the file stays under --max-mb

    with tempfile.TemporaryDirectory() as tmp:
        # text goes through textfile= so commas and colons in it need no filtergraph escaping
        font = f"fontfile={ff_path(FONT)}:" if FONT.exists() else ""

        def fit(s, width):
            return round(min(h / 24, width / (0.56 * len(s) + 2)))

        def text(name, s, width, x, y, size=None):
            (Path(tmp) / f"{name}.txt").write_text(s, encoding="utf-8")
            size = size or fit(s, width)
            return (f"drawtext={font}textfile={name}.txt:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:"
                    f"boxborderw={round(size / 3)}:x={x}:y={y}")

        m = round(h / 40)
        stretch = "" if still else f"setpts={args.slow:g}*PTS,"
        graph = (f"[0:v]{stretch}fps={args.fps:g},scale={widths[0]}:{h}:flags=lanczos,setsar=1,"
                 f"{text('real', args.real_label, widths[0], m, m)}[r];"
                 f"[1:v]{sim_fix}fps={args.fps:g},scale={widths[1]}:{h}:flags=lanczos:out_range=tv,setsar=1,"
                 f"{text('sim', args.sim_label, widths[1], m, m)}[s];"
                 f"[r][s]hstack=inputs=2")
        if args.caption:                  # in a bar of its own under both halves, clear of the sim clock
            # one drawtext per line: this drawtext shapes a newline as a missing-glyph box
            rows = args.caption.split("\\n")
            size = min(fit(r, sum(widths)) for r in rows)
            step = round(size * 1.45)
            bar = (round(h / 16) + step * (len(rows) - 1)) // 2 * 2
            graph += f",pad=iw:ih+{bar}:0:0:black"
            for i, r in enumerate(rows):
                y = f"h-{bar // 2}-text_h/2+{round((i - (len(rows) - 1) / 2) * step)}"
                graph += "," + text(f"caption{i}", r, sum(widths), "(w-text_w)/2", y, size)
        if args.loops > 1:
            graph += f",loop=loop={args.loops - 1}:size={round(span * args.fps) + 5}:start=0,setpts=N/{args.fps:g}/TB"
        graph += ",format=yuv420p[v]"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        real_in = (["-loop", "1", "-framerate", f"{args.fps:g}", "-t", f"{span}"] if still else
                   ["-ss", f"{args.real_start}", "-t", f"{span / args.slow}"])
        cmd = ["ffmpeg", "-v", "error", "-y", *real_in, "-i", str(args.real.resolve()),
               "-ss", f"{args.sim_start}", "-t", f"{span}", "-i", str(args.sim.resolve()),
               "-filter_complex", graph, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
               "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k", "-movflags", "+faststart", str(args.out.resolve())]
        subprocess.run(cmd, check=True, cwd=tmp)
    p = probe(args.out)
    print(f"side_by_side: wrote {args.out} ({p['width']}x{p['height']}, {p['duration']:.2f} s = {args.loops} x "
          f"{span:.2f} s, {args.out.stat().st_size / 1e6:.1f} MB){' [sim range fixed: full-range WebM]' if sim_fix else ''}")


if __name__ == "__main__":
    main()
