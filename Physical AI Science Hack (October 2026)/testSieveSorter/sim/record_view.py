"""Render a recorded run's replay page to an MP4, frame-exact, through headless Chrome.

Run from sim\\:  python record_view.py <run_dir> [--view "?cam=...&target=...&fov=..&aspect=.."] [-o clip.mp4]
The page's Record button records in real time, so its frame rate depends on the machine. This script
instead steps the page (run_dir/view.html, from viewer.py) to t = k * speed / fps for every frame k,
takes each frame from the page's viewerExport hook (zone labels and sim clock included) and pipes the
JPEGs into ffmpeg. --view takes what the page's Copy camera button copies (the whole URL or just the
query). Needs Chrome or Edge, ffmpeg on PATH, and websockets (the venv has it: mujoco depends on it).
"""
import argparse
import base64
import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from websockets.sync.client import connect

BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "google-chrome", "chromium", "chromium-browser"]


class Page:
    """One page target over the DevTools protocol (flattened session on the browser socket)."""

    def __init__(self, browser: str, width: int, height: int):
        self.profile = tempfile.mkdtemp(prefix="record_view_")
        # --use-angle=d3d11 renders WebGL on the GPU on Windows; SwiftShader is the CPU fallback.
        self.proc = subprocess.Popen(
            [browser, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={self.profile}",
             f"--window-size={width + 460},{max(height, 600)}", "--no-first-run", "--no-default-browser-check",
             "--use-angle=d3d11", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self.profile) / "DevToolsActivePort"
        for _ in range(100):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.1)
        port, path = port_file.read_text().split()[:2]
        self.stack = contextlib.ExitStack()
        self.ws = self.stack.enter_context(connect(f"ws://127.0.0.1:{port}{path}", max_size=None))
        self.n = 0
        target = self.call("Target.createTarget", url="about:blank")["targetId"]
        self.session = self.call("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]

    def call(self, method: str, session: bool = False, **params):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params}
        if session:
            msg["sessionId"] = self.session
        self.ws.send(json.dumps(msg))
        while True:                       # skip events until our reply
            reply = json.loads(self.ws.recv())
            if reply.get("id") == self.n:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply.get("result", {})

    def eval(self, expr: str):
        r = self.call("Runtime.evaluate", session=True, expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(f"page: {r['exceptionDetails'].get('exception', {}).get('description', r['exceptionDetails'])}")
        return r["result"].get("value")

    def close(self):
        try:
            self.call("Browser.close")
        except Exception:
            pass
        self.stack.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


def view_query(view: str | None) -> str:
    """'?cam=..' or a whole Copy camera URL -> 'cam=..&target=..' (page options only)."""
    if not view:
        return ""
    view = view.strip()
    return urlsplit(view).query if "://" in view else view.lstrip("?#")


def frame_size(query: str, height: int) -> tuple[int, int]:
    """Width from the page's aspect option (fill means 16:9), height as given; both even."""
    a = parse_qs(query).get("aspect", ["16:9"])[0]
    try:
        w, h = (float(x) for x in a.split(":"))
        ratio = w / h
    except ValueError:
        ratio = 16 / 9
    return round(height * ratio / 2) * 2, height // 2 * 2


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--view", help="camera from the page's Copy camera button (URL or ?query)")
    ap.add_argument("--height", type=int, default=1080, help="frame height in px (default 1080)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--speed", type=float, default=1.0, help="sim seconds per video second (default 1)")
    ap.add_argument("--start", type=float, default=0.0, help="sim time to start at, s from the start")
    ap.add_argument("--duration", type=float, help="sim seconds to render (default: to the end)")
    ap.add_argument("-o", "--out", type=Path, help="output .mp4 (default run_dir/sim_clip.mp4)")
    args = ap.parse_args()

    page_file = (args.run_dir / "view.html").resolve()
    if not page_file.exists():
        raise SystemExit(f"record_view: {page_file} not found; run viewer.py {args.run_dir} first")
    browser = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if not browser:
        raise SystemExit("record_view: no Chrome or Edge found")
    query = view_query(args.view)
    w, h = frame_size(query, args.height)
    out = args.out or args.run_dir / "sim_clip.mp4"

    page = Page(browser, w, h)
    try:
        page.call("Page.enable", session=True)
        page.call("Page.navigate", session=True, url=page_file.as_uri() + ("?" + query if query else ""))
        for _ in range(300):              # the hook appears once the trajectory is decoded
            if page.eval("typeof window.viewerExport === 'object'"):
                break
            time.sleep(0.1)
        else:
            raise SystemExit("record_view: the page never became ready (viewer_template.html too old?)")
        page.eval(f"viewerExport.size({w}, {h}, {h / 600:.3f})")
        print(f"record_view: renderer {page.eval(_GPU)}")
        span = page.eval("viewerExport.duration") - args.start
        if args.duration is not None:
            span = min(span, args.duration)
        n = int(span / args.speed * args.fps) + 1
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", f"{args.fps:g}", "-c:v", "mjpeg",
               "-i", "-", "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",   # JPEGs are full range
               "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-color_range", "tv",
               "-movflags", "+faststart", str(out)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t_wall = time.time()
        for k in range(n):
            ts = args.start + k * args.speed / args.fps
            url = page.eval(f"viewerExport.frame({ts:.6f}, {args.speed:g})")
            ff.stdin.write(base64.b64decode(url.split(",", 1)[1]))
            if k % 60 == 0:
                print(f"\rrecord_view: frame {k + 1}/{n}", end="", flush=True)
        ff.stdin.close()
        if ff.wait():
            raise SystemExit("record_view: ffmpeg failed")
    finally:
        page.close()
    print(f"\rrecord_view: wrote {out} ({w}x{h}, {n} frames at {args.fps:g} fps = {n / args.fps:.2f} s, "
          f"{out.stat().st_size / 1e6:.1f} MB, {time.time() - t_wall:.0f} s to render)")


_GPU = ("(() => { const g = document.createElement('canvas').getContext('webgl2');"
        " const e = g && g.getExtension('WEBGL_debug_renderer_info');"
        " return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'unknown'; })()")

if __name__ == "__main__":
    main()
