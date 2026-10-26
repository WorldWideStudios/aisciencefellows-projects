"""Loopback-only JSON API and production web server; no network configuration changes."""
import argparse
import json
import secrets
import signal
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .devices import device_inventory
from .model import JOINTS, ROOT, Store, UNITS
from .runtime import Runtime


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, runtime, directory, dev_origin=None):
        self.runtime = runtime
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, partial(Handler, directory=str(directory)))
        port = self.server_address[1]
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.origins = {f"http://{host}" for host in self.hosts}
        if dev_origin:
            parsed = urlsplit(dev_origin)
            if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1"):
                raise ValueError("Development origin must be a loopback HTTP URL")
            self.origins.add(dev_origin.rstrip("/"))


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if len(args) < 2 or str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)

    def _json(self, status, value):
        encoded = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _host_allowed(self):
        if self.headers.get("Host") not in self.server.hosts:
            self._json(403, {"error": "Only this server's loopback host is allowed"})
            return False
        return True

    def do_GET(self):
        if not self._host_allowed():
            return
        route = urlsplit(self.path).path
        rt = self.server.runtime
        try:
            if route == "/api/bootstrap":
                self._json(200, {"token": self.server.token, "joints": JOINTS, "units": UNITS,
                                 "state": rt.state(), "arms": rt.config, "sequences": rt.store.list()})
            elif route == "/api/state":
                self._json(200, rt.state())
            elif route == "/api/sequences":
                self._json(200, {"sequences": rt.store.list()})
            elif route == "/api/ports":
                self._json(200, device_inventory(rt.config))
            elif route.startswith("/api/"):
                self._json(404, {"error": "Unknown endpoint"})
            else:
                super().do_GET()
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def do_POST(self):
        if not self._host_allowed():
            return
        if self.headers.get("Origin") not in self.server.origins | {None}:
            self._json(403, {"error": "Cross-origin control is not allowed"})
            return
        if not secrets.compare_digest(self.headers.get("X-Studio-Token", ""), self.server.token):
            self._json(403, {"error": "Session expired. Refresh the page before controlling the arm."})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self._json(415, {"error": "JSON requests are required"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1_000_000:
                raise ValueError("Request must contain 1–1,000,000 bytes")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Request must be a JSON object")
            result = self._action(urlsplit(self.path).path, payload)
            self._json(200, result)
        except (ValueError, KeyError, TypeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _action(self, route, data):
        rt = self.server.runtime
        if route == "/api/connect":
            if not isinstance(data.get("leader", True), bool):
                raise ValueError("leader must be true or false")
            rt.connect(data["mode"], data.get("leader", True))
        elif route == "/api/simulation":
            rt.set_simulation(data["pose"])
        elif route == "/api/record":
            return {"sequence": rt.record(data["sequence_id"], data["revision"], data["name"])}
        elif route == "/api/sequence/save":
            return {"sequence": rt.save_sequence(data["sequence_id"], data["sequence"], data["revision"])}
        elif route == "/api/sequence/create":
            return {"sequence": rt.store.create(data["sequence"])}
        elif route == "/api/plan":
            return {"plan": rt.make_plan(data["sequence_id"], data["revision"], data["speed"], data["acceleration"])}
        elif route == "/api/review":
            rt.review(data["plan_id"])
        elif route == "/api/execute":
            rt.execute(data["plan_id"], data["client"])
        elif route == "/api/teleop":
            rt.teleoperate(data["client"])
        elif route == "/api/stop":
            rt.stop()
        elif route == "/api/release":
            rt.release()
        elif route == "/api/heartbeat":
            rt.heartbeat(data.get("client"))
        else:
            raise ValueError("Unknown action")
        return {"state": rt.state()}


def main():
    parser = argparse.ArgumentParser(description="SO-101 local sequence studio")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--enable-hardware", action="store_true", help="Allow explicit browser connections to the USB arms")
    parser.add_argument("--arms", type=Path, default=ROOT / "arms.json")
    parser.add_argument("--data", type=Path, default=ROOT / "data/sequences.json")
    parser.add_argument("--web", type=Path, default=ROOT / "robot_viewer/dist")
    parser.add_argument("--dev-origin", help="Allow a loopback Vite origin, e.g. http://127.0.0.1:5173")
    options = parser.parse_args()
    if not (options.web / "index.html").exists() and not options.dev_origin:
        parser.error("Build the browser first: cd robot_viewer && npm ci && npm run build")
    rt = Runtime(Store(options.data), json.loads(options.arms.read_text()), options.enable_hardware)
    server = StudioServer(("127.0.0.1", options.port), rt, options.web, options.dev_origin)
    def shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    rt.start()
    print(f"SO-101 Sequence Studio: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Hardware {'available on explicit connection' if options.enable_hardware else 'disabled'} · library: {options.data}", flush=True)
    try:
        server.serve_forever()
    finally:
        rt.close()
        server.server_close()


if __name__ == "__main__":
    main()
