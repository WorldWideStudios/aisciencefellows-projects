"""FileHandoff — the loop with a human (or a robot) in it.

Ported from green-knight's `bridge.py`, where it carried the whole bench path.
The shape is domain-independent and it is the cheapest possible integration with
a system you do not control:

    we write   <work_dir>/<name>.request.<ext>    "here is what to do"
    they do    the thing                          (robot, operator, web UI)
    they drop  <work_dir>/<name>.result.<ext>     whatever came back
    we read    it and carry on

That is the same relationship we have with Zeon: workflows run through the web
UI, not our process, so we hand a file over and wait for one back. Nothing here
touches the network, so it works identically against a robot, a simulator, or a
person typing a result by hand — which is also the escape hatch when everything
else is down.
"""

import os
import time
from typing import Callable, Optional

#: Floor on the polling interval. A zero interval turns the wait into a busy
#: spin that never reaches its timeout — this bit us twice on green-knight.
MIN_POLL_INTERVAL_S = 0.05


class FileHandoff:
    """Write a request file, wait for a result file, return its contents."""

    def __init__(self, work_dir: str, poll_interval_s: float = 5.0,
                 timeout_s: float = 3600.0,
                 sleep: Callable[[float], None] = time.sleep,
                 announce: Callable[[str], None] = print):
        self.work_dir = str(work_dir)
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        self.sleep = sleep
        self.announce = announce
        os.makedirs(self.work_dir, exist_ok=True)

    def request_path(self, name: str, ext: str = "json") -> str:
        return os.path.join(self.work_dir, f"{name}.request.{ext}")

    def result_path(self, name: str, ext: str = "json") -> str:
        return os.path.join(self.work_dir, f"{name}.result.{ext}")

    def _retire_stale_result(self, name: str, ext: str) -> None:
        """Move an existing result aside before waiting for a new one.

        The wait loop only asks "does this file exist", so a result left over
        from an earlier attempt is returned instantly as if it were fresh. That
        is how you change a parameter, re-run, and get told nothing changed.
        """
        path = self.result_path(name, ext)
        if not os.path.exists(path):
            return
        n = 1
        while os.path.exists(f"{path}.superseded-{n}"):
            n += 1
        os.rename(path, f"{path}.superseded-{n}")
        self.announce(f"  NOTE: an old result for {name!r} was set aside, not "
                      f"reused. Waiting for a fresh one.")

    def send(self, name: str, body: str, ext: str = "json",
             instructions: Optional[str] = None) -> str:
        """Write the request and block until a result appears. Returns its text."""
        self._retire_stale_result(name, ext)
        req = self.request_path(name, ext)
        with open(req, "w") as f:
            f.write(body)

        res = self.result_path(name, ext)
        self.announce(instructions or "\n".join([
            "",
            f"=== handoff: {name} ===",
            f"  request : {req}",
            f"  when done, write the result to:",
            f"      {res}",
            f"  waiting (every {self.poll_interval_s:g}s, giving up after "
            f"{self.timeout_s / 60:.0f} min)...",
            "",
        ]))

        waited = 0.0
        while not os.path.exists(res):
            if waited >= self.timeout_s:
                raise TimeoutError(
                    f"No result after {self.timeout_s / 60:.0f} min. Expected a "
                    f"file at {res}.")
            interval = max(self.poll_interval_s, MIN_POLL_INTERVAL_S)
            self.sleep(interval)
            waited += interval

        with open(res) as f:
            out = f.read()
        self.announce(f"  read {len(out)} bytes from {res}\n")
        return out
