#!/usr/bin/env python3
"""Trigger the tactile shaker: play low sine pulses out of the Pi's headphone jack.

  python3 buzz.py                      one 1-second buzz at 50 Hz
  python3 buzz.py -f 40 -s 0.5 -n 3    three half-second buzzes at 40 Hz
  python3 buzz.py -v 0.5               half strength
  python3 buzz.py -f 100 -t 30 -s 6    glide from 100 Hz down to 30 Hz over 6 seconds
"""
import argparse
import io
import math
import struct
import subprocess
import sys
import wave

RATE = 44100


def tone(freq, seconds, volume, to=None):
    n = int(RATE * seconds)
    fade = max(1, min(int(RATE * 0.01), n // 2))  # 10 ms ramp so pulses start and stop without a click
    to = to or freq
    out = bytearray()
    phase = 0.0
    for i in range(n):
        phase += 2 * math.pi * freq * (to / freq) ** (i / n) / RATE  # glides freq -> to when sweeping
        env = min(1.0, i / fade, (n - 1 - i) / fade)
        s = int(32767 * volume * env * math.sin(phase))
        out += struct.pack('<hh', s, s)
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-f', '--freq', type=float, default=50, help='Hz, 30-120 is felt more than heard (default 50)')
    p.add_argument('-t', '--to', type=float, help='sweep from --freq to this Hz over each pulse')
    p.add_argument('-s', '--seconds', type=float, default=1.0, help='length of each pulse (default 1)')
    p.add_argument('-n', '--pulses', type=int, default=1, help='number of pulses (default 1)')
    p.add_argument('-g', '--gap', type=float, default=0.3, help='silence between pulses (default 0.3)')
    p.add_argument('-v', '--volume', type=float, default=1.0, help='0.0-1.0 (default 1.0)')
    p.add_argument('-d', '--device', help='ALSA device (default: headphone jack, then system default)')
    a = p.parse_args()

    pulse = tone(a.freq, a.seconds, max(0.0, min(1.0, a.volume)), a.to)
    gap = bytes(4 * int(RATE * a.gap))
    frames = gap.join([pulse] * a.pulses)

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)

    # the Pi restores the headphone jack to about 78% (-20 dB) on boot; volume is controlled with -v instead
    subprocess.run(['amixer', '-q', '-c', 'Headphones', 'sset', 'PCM', '100%'], stderr=subprocess.DEVNULL)
    for dev in [a.device] if a.device else ['plughw:CARD=Headphones', 'default']:
        r = subprocess.run(['aplay', '-q', '-D', dev, '-'], input=buf.getvalue(), stderr=subprocess.PIPE)
        if r.returncode == 0:
            return 0
        print(f'{dev}: {r.stderr.decode().strip()}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
