"""PC Control API (Generation 3); see references/pc-control-protocol.md.

No legacy action opcodes, calibration writes, automatic homing, or motion retries.
"""
from decimal import Decimal, InvalidOperation
import struct
import time
from . import transport as v

STATES = {0: 'Ready', 1: 'Waiting for blow-in', 2: 'Waiting for RUN key',
          3: 'Busy', 4: 'Pipette not homed', 5: 'User aborted'}


def identity(packet):
    if len(packet) != 20:
        raise v.ProtocolError(f'PC Control identity must be 20 bytes; received {len(packet)}. Check PC Control (ComM) mode.')
    return {'serial': f'{int.from_bytes(packet[14:18], "big"):08d}',
            'firmware': f'{packet[10]}.{packet[11]}', 'hardware': packet[13],
            'model_code': int.from_bytes(packet[18:20], 'big')}


def action_status(packet):
    if len(packet) != 14:
        raise v.ProtocolError(f'Expected 14-byte action status, received {len(packet)}')
    state, hardware = struct.unpack('>HH', packet[10:14])
    if state not in STATES:
        raise v.ProtocolError(f'Unknown action status {state}')
    if hardware:
        raise v.ProtocolError(f'Pipette hardware error {hardware}')
    return {'code': state, 'state': STATES[state], 'hardware_error': hardware}


def volume_units(value):
    try:
        amount = Decimal(str(value)) * 10
        if not amount.is_finite() or amount != amount.to_integral_value() or not 1 <= amount <= 1250:
            raise ValueError('Volume must be 0.1–125 µL in increments of 0.1 µL')
        return int(amount)
    except InvalidOperation:
        raise ValueError('Enter a volume in µL') from None


def action_body(code, speed, units, message='VIAFLO PC control'):
    if code not in (1, 7, 4):
        raise ValueError('Unsupported PC-control action')
    if type(speed) is not int or not 1 <= speed <= 10:
        raise ValueError('Speed must be 1–10')
    if type(units) is not int or not 0 <= units <= 1250:
        raise ValueError('Volume exceeds 125 µL')
    # action, speed, volume (0.1 µL), mix cycles, RUN confirmation,
    # 20-byte display message, spacing (unused on this single-channel pipette).
    return struct.pack('>BBHBB', code, speed, units, 0, 0) + message.encode('ascii')[:20].ljust(20, b' ') + b'\x00\x00'


class Controller:
    def __init__(self):
        self.link = None
        self.identity = None
        self.current = None
        self.loaded_units = None

    def disconnect(self):
        if self.link:
            self.link.close()
        self.link = self.identity = self.current = self.loaded_units = None

    def require(self):
        if self.link is None:
            raise ValueError('Connect and verify the pipette first')

    def connect(self, **kwargs):
        self.disconnect()
        try:
            self.link = v.Link(**kwargs, remote=True)
            return {'identity': self.read_identity(), 'status': self.read_status()}
        except Exception:
            self.disconnect()
            raise

    def read_identity(self):
        self.require()
        info = identity(self.link.transact(1))
        # Explicit, user-identified hardware profile. Model enum in the published
        # DLL differs from this firmware; do not map unknown codes by guessing.
        if (info['serial'], info['firmware'], info['hardware'], info['model_code']) != ('07064070', '5.10', 5, 12):
            raise v.ProtocolError(f'Pipette differs from the confirmed 125 µL single-channel profile: {info}')
        info.update(model='125 µL single channel (confirmed)', capacity_ul=125)
        self.identity = info
        return info

    def read_status(self):
        self.require()
        self.current = action_status(self.link.transact(2))
        return self.current

    def confirm_empty(self):
        if self.read_status()['code'] != 0:
            raise ValueError('Pipette must report Ready before confirming empty')
        self.loaded_units = 0
        self.link.record(event='operator_confirmed_empty')
        return {'tracked_volume_ul': 0, 'basis': 'operator confirmed empty'}

    def _wait_ready(self, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.read_status()
            if status['code'] == 0:
                return status
            if status['code'] != 3:
                raise v.ProtocolError(status['state'] + '; inspect pipette before further commands')
            time.sleep(0.2)
        raise TimeoutError('Pipette remained busy. Inspect it; motion will not be retried.')

    def _action(self, code, units, speed):
        packet = self.link.transact(5, action_body(code, speed, units))
        if len(packet) != 10:
            raise v.ProtocolError('Unexpected SetAction acknowledgment length')
        return self._wait_ready()

    def motion(self, action, volume, speed):
        self.require()
        if not self.identity:
            raise ValueError('Verified identity required')
        if action not in ('aspirate', 'dispense', 'cycle', 'purge'):
            raise ValueError('Unsupported action')
        if type(speed) is not int or not 1 <= speed <= 10:
            raise ValueError('Speed must be 1–10')
        units = volume_units(volume) if action != 'purge' else 0
        if self.loaded_units is None:
            raise ValueError('Confirm the pipette is empty before enabling motion')
        start = self.loaded_units
        target = start - units if action == 'dispense' else start + units
        if action != 'purge' and not 0 <= target <= 1250:
            raise ValueError(f'Move exceeds tracked volume bounds (currently {start/10:g} µL)')
        try:
            if self.read_status()['code'] != 0:
                raise v.ProtocolError('Pipette is not Ready; inspect its display')
            self._action({'aspirate': 1, 'dispense': 7, 'cycle': 1, 'purge': 4}[action], units, speed)
            self.loaded_units = 0 if action == 'purge' else target
            if action == 'cycle':
                self._action(7, units, speed)
                self.loaded_units = start
            result = {'action': action, 'requested_ul': units/10, 'status': self.current,
                      'tracked_volume_ul': self.loaded_units/10,
                      'note': 'Command acknowledged and Ready reported; volume is tracked, not measured.'}
            self.link.record(event='pc_motion', **result)
            return result
        except Exception:
            self.disconnect()
            raise
