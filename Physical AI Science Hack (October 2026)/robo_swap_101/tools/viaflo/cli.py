"""Small terminal interface for the verified Generation 3 VIAFLO profile."""
import argparse
import json
import shlex
import subprocess
import sys

from . import transport
from .pc_control import Controller

HELP = """Commands (volumes in µL; speed defaults to 1):
  status                     Read device state and tracked volume
  identity                   Read and verify pipette identity
  confirm-empty              Assert that you physically verified empty
  aspirate UL [SPEED]         Aspirate 0.1–125 µL
  dispense UL [SPEED]         Dispense without blowout
  cycle UL [SPEED]            Aspirate then dispense the same volume
  purge [SPEED]              Expel remaining contents (includes blowout)
  help                       Show commands
  quit                       Disconnect
Tracking is commanded volume, not a measurement. Reconnection resets it.
"""


def show(value):
    print(json.dumps(value, indent=2))


def execute(controller, line):
    """Execute one shell command; return False to disconnect."""
    args = shlex.split(line)
    if not args:
        return True
    command, *values = args
    if command in ('quit', 'exit') and not values:
        return False
    if command == 'help' and not values:
        print(HELP)
    elif command == 'status' and not values:
        show({'status': controller.read_status(),
              'tracked_volume_ul': None if controller.loaded_units is None else controller.loaded_units / 10})
    elif command == 'identity' and not values:
        show(controller.read_identity())
    elif command == 'confirm-empty' and not values:
        show(controller.confirm_empty())
    elif command in ('aspirate', 'dispense', 'cycle') and 1 <= len(values) <= 2:
        show(controller.motion(command, values[0], int(values[1]) if len(values) == 2 else 1))
    elif command == 'purge' and len(values) <= 1:
        show(controller.motion('purge', 0, int(values[0]) if values else 1))
    else:
        raise ValueError('Unknown command or arguments. Type help.')
    return True


def build_helper():
    root = transport.ROOT
    subprocess.run(['clang', '-fobjc-arc', '-framework', 'Foundation',
                    '-framework', 'IOBluetooth', str(root / 'bluetooth.m'),
                    '-o', str(root / 'bluetooth'),
                    f'-Wl,-sectcreate,__TEXT,__info_plist,{root / "Info.plist"}'], check=True)
    print(f'Built {root / "bluetooth"}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build', help='Build the native macOS Bluetooth transport')
    for name in ('paired', 'scan', 'ports'):
        sub.add_parser(name)
    for name in ('status', 'shell'):
        p = sub.add_parser(name)
        target = p.add_mutually_exclusive_group(required=True)
        target.add_argument('--address', help='Exact pipette Bluetooth address')
        target.add_argument('--port', help='Exact serial device path')
        p.add_argument('--baud', type=int, help='Documented serial baud rate')
        p.add_argument('--channel', type=int, choices=range(1, 31), metavar='1..30')
    args = parser.parse_args(argv)
    if getattr(args, 'port', None) and (not args.baud or args.baud <= 0):
        parser.error('--port requires a positive, documented --baud')
    if getattr(args, 'address', None) and args.baud is not None:
        parser.error('--baud is only valid with --port')
    if getattr(args, 'port', None) and args.channel is not None:
        parser.error('--channel is only valid with --address')
    controller = Controller()
    try:
        if args.command == 'build':
            build_helper()
        elif args.command in ('paired', 'scan'):
            return subprocess.run([str(transport.ROOT / 'bluetooth'), args.command], timeout=30).returncode
        elif args.command == 'ports':
            from serial.tools.list_ports import comports
            for port in comports():
                print(port.device, port.description)
        else:
            show(controller.connect(address=args.address, port=args.port, baud=args.baud, channel=args.channel))
            if args.command == 'shell':
                print(HELP)
                while True:
                    try:
                        line = input('viaflo> ')
                    except EOFError:
                        break
                    try:
                        if not execute(controller, line):
                            break
                    except ValueError as error:
                        print(f'Input rejected: {error}', file=sys.stderr)
        return 0
    except KeyboardInterrupt:
        print('\nDisconnected. If interrupted during motion, inspect the pipette before reconnecting.', file=sys.stderr)
        return 130
    except (OSError, RuntimeError, TimeoutError, ImportError, subprocess.SubprocessError) as error:
        print(f'FAILED: {error}\nDisconnected; no automatic retry. Inspect the pipette before reconnecting.', file=sys.stderr)
        if isinstance(error, FileNotFoundError):
            print('For Bluetooth, first run: python viaflo_control.py build', file=sys.stderr)
        return 1
    finally:
        controller.disconnect()
