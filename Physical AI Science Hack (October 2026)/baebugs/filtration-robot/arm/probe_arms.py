"""Read-only probe: ping motors 1-6 on each port and report voltage and position."""
import sys

import scservo_sdk as scs
from serial import SerialException

# STS3215 control table addresses
MAX_VOLTAGE_LIMIT = 14  # 1 byte, units of 0.1 V; tells the 7.4 V and 12 V variants apart
TORQUE_ENABLE = 40  # 1 byte
PRESENT_POSITION = 56  # 2 bytes
PRESENT_VOLTAGE = 62  # 1 byte, units of 0.1 V
PRESENT_TEMPERATURE = 63  # 1 byte, deg C
STATUS = 65  # 1 byte, error flags (bit 0 = voltage error)
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

for port in sys.argv[1:]:
    ph = scs.PortHandler(port)
    pk = scs.PacketHandler(0)
    try:
        opened = ph.openPort()
    except SerialException:
        opened = False
    if not opened:
        print(f"== {port}: cannot open (in use by another program, e.g. mirroring?)")
        continue
    ph.setBaudRate(1_000_000)
    print(f"== {port}")
    for mid, name in enumerate(NAMES, start=1):
        model, res, _ = pk.ping(ph, mid)
        if res != scs.COMM_SUCCESS:
            print(f"  id {mid} {name:13s}: no response")
            continue
        volt, _, _ = pk.read1ByteTxRx(ph, mid, PRESENT_VOLTAGE)
        pos, _, _ = pk.read2ByteTxRx(ph, mid, PRESENT_POSITION)
        vmax, _, _ = pk.read1ByteTxRx(ph, mid, MAX_VOLTAGE_LIMIT)
        torque, _, _ = pk.read1ByteTxRx(ph, mid, TORQUE_ENABLE)
        temp, _, _ = pk.read1ByteTxRx(ph, mid, PRESENT_TEMPERATURE)
        status, _, _ = pk.read1ByteTxRx(ph, mid, STATUS)
        print(
            f"  id {mid} {name:13s}: model {model}, {volt / 10:.1f} V (max {vmax / 10:.1f} V), "
            f"{temp} C, torque {torque}, status 0b{status:08b}, position {pos}"
        )
    ph.closePort()
