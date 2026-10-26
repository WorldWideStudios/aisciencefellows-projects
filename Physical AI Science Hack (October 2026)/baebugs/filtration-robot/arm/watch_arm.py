"""Read-only: sample every motor's position on one port for a few seconds and report min/max and read errors.

Usage: python watch_arm.py COM6 [seconds]
"""
import sys
import time

import scservo_sdk as scs
from serial import SerialException

PRESENT_POSITION = 56  # 2 bytes
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

port = sys.argv[1]
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 5

ph = scs.PortHandler(port)
pk = scs.PacketHandler(0)
try:
    opened = ph.openPort()
except SerialException:
    opened = False
if not opened:
    sys.exit(f"{port}: cannot open (in use by another program, e.g. mirroring?)")
ph.setBaudRate(1_000_000)

stats = {name: {"min": None, "max": None, "last": None, "errors": 0, "reads": 0} for name in NAMES}
if sys.stdin.isatty():
    input(f"Press ENTER to start recording {port} for {seconds:g} s...")
    print("Recording - move the joints now.")
end = time.time() + seconds
while time.time() < end:
    for mid, name in enumerate(NAMES, start=1):
        s = stats[name]
        pos, res, err = pk.read2ByteTxRx(ph, mid, PRESENT_POSITION)
        s["reads"] += 1
        if res != scs.COMM_SUCCESS or err != 0:
            s["errors"] += 1
            continue
        s["last"] = pos
        s["min"] = pos if s["min"] is None else min(s["min"], pos)
        s["max"] = pos if s["max"] is None else max(s["max"], pos)
ph.closePort()

print(f"== {port}, {seconds:g} s")
for name, s in stats.items():
    print(
        f"  {name:13s}: min {s['min']}, max {s['max']}, last {s['last']}, "
        f"{s['reads']} reads, {s['errors']} errors"
    )
