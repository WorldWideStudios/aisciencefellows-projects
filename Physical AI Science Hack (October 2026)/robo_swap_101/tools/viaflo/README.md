# VIAFLO terminal control

This imports the PC Control driver and native macOS Classic Bluetooth transport
from `/Users/neilson/Desktop/robo_swap/tools/viaflo` (copied 2026-10-24).
The GUI, legacy Vision motion commands, binaries, environments, and device logs
were excluded. Packet framing derives from the Willow Garage BSD driver; its
notice is retained in [LICENSE](LICENSE). Protocol provenance and prior hardware
observations are retained in [references/pc-control-protocol.md](references/pc-control-protocol.md).
Those observations describe the source project's September tests, not new hardware
validation in this repository.

## Setup on this Mac

From the repository root:

```sh
python3 viaflo_control.py build
python3 viaflo_control.py paired
```

The build requires Apple's Command Line Tools (`clang`, Foundation, IOBluetooth).
Bluetooth uses the native helper, with no Python Bluetooth dependency. Allow the
Terminal/Codex Bluetooth permission if macOS asks. If needed, pair the exact
pipette in macOS Bluetooth settings; the documented PIN is `12345`. `scan` offers
bounded discovery but can time out on macOS; `paired` lists cached pairings and
does not prove the device is reachable. No command changes network settings or
resets an adapter.

On the pipette choose **Toolbox → Communications → PC Control (ComM)**.
The verified source device is Bluetooth address `00-16-a4-4c-9a-ac`, serial
`07064070`, 125 µL single channel, firmware 5.10, hardware 5, raw model code 12.
The driver requires that exact identity tuple. Other pipettes need a separately
verified profile; do not simply remove the identity guard. Legacy Vision and
VIALINK modes do not use these motion commands.

Read identity and state without motion:

```sh
python3 viaflo_control.py status --address 00-16-a4-4c-9a-ac
```

Start an interactive connection:

```sh
python3 viaflo_control.py shell --address 00-16-a4-4c-9a-ac
```

Connection reads identity and status only. After physically checking that the
pipette is empty and the tip is out of liquid, a first dry test is:

```text
viaflo> confirm-empty
viaflo> cycle 5
viaflo> status
```

`confirm-empty` is your assertion of empty; it does not move or empty the pipette.
For liquid handling, position the tip appropriately before each action:

```text
viaflo> aspirate 10
viaflo> dispense 5
viaflo> dispense 5
viaflo> quit
```

Commands: `identity`, `status`, `confirm-empty`, `aspirate UL [SPEED]`,
`dispense UL [SPEED]`, `cycle UL [SPEED]`, `purge [SPEED]`, `help`, `quit`.
Volumes are 0.1–125 µL in 0.1 µL increments; speed is 1–10, default 1.
Dispense omits blowout; purge expels remaining contents and includes blowout.
`cycle` aspirates then dispenses at the current physical location; it does not
move the robot. There is no robot integration or tip-eject command.

Volume tracking persists within a shell session. It starts unknown and is based
on acknowledged commands, not measured contents or piston telemetry. Reconnect
requires checking empty again. Do not manually change pipette contents during a
tracked session. Failed communication or motion ends the session; inspect the
pipette because a timed-out command may have moved it. No automatic resend,
compensating dispense, homing, calibration write, or firmware change is made.
Ctrl-C disconnects; it is **not** an emergency motor stop.

## Optional serial connection

```sh
uv pip install --python .venv/bin/python -r requirements-viaflo.txt
.venv/bin/python viaflo_control.py ports
.venv/bin/python viaflo_control.py shell --port /dev/cu.ACTUAL_DEVICE --baud DOCUMENTED_BAUD
```

Use a compatible INTEGRA communication accessory, the correct PC Control wired
mode, and its documented baud rate. This repository has not verified a wired
connection. Bluetooth RFCOMM channel can be set explicitly with `--channel 1`;
otherwise the helper uses the cached Serial Port service, falling back to 1.

Packet transcripts are written to `tools/viaflo/logs/` and ignored by Git.
Build output is also ignored. Run software tests without hardware:

```sh
python3 -m unittest discover -s tests -v
```
