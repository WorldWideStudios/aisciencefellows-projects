import struct
import unittest
from unittest.mock import patch
from tools.viaflo import transport as v
from tools.viaflo import pc_control as pc


def packet(kind, body=b'', status=0, seq=1):
    wire = v.frame(kind, status.to_bytes(2, 'big') + body, seq)
    p = v.Decoder().feed(wire)[0]
    return v.response(p, seq, kind, 2)


class Fake:
    def __init__(self, failure=None):
        self.sent = []
        self.failure = failure
        self.closed = False

    def transact(self, kind, body=b'', timeout=5):
        self.sent.append((kind, body))
        if kind == 1:
            return bytes.fromhex('00148f00010000010000050a0005006bca06000c')
        if kind == 2:
            return packet(2, struct.pack('>HH', 0, 0))
        if kind == 5:
            if self.failure:
                raise self.failure
            return packet(5)
        raise AssertionError(f'Forbidden or unexpected opcode: {kind}')

    def record(self, **kwargs): pass
    def close(self): self.closed = True


class Tests(unittest.TestCase):
    def controller(self, failure=None):
        f = Fake(failure)
        c = pc.Controller()
        with patch.object(v, 'Link', return_value=f):
            c.connect(address='00-16-a4-4c-9a-ac')
        return c, f

    def test_actual_fragmented_identity(self):
        d = v.Decoder()
        self.assertEqual(d.feed(bytes.fromhex('0200148f00010000010000')), [])
        p = d.feed(bytes.fromhex('050a0005006bca06000c03'))[0]
        info = pc.identity(v.response(p, 1, 1, 2))
        self.assertEqual(info, dict(serial='07064070', firmware='5.10', hardware=5, model_code=12))

    def test_low_byte_error_is_rejected(self):
        for status in (1, 2, 3, 4, 256):
            with self.assertRaises(v.ProtocolError): packet(5, status=status)

    def test_connect_only_sends_reads(self):
        c, f = self.controller()
        self.assertEqual([x[0] for x in f.sent], [1, 2])
        self.assertIsNone(c.loaded_units)
        with self.assertRaises(ValueError): c.motion('cycle', 5, 1)
        self.assertEqual([x[0] for x in f.sent], [1, 2])

    def test_cycle_and_volume_bounds(self):
        c, f = self.controller()
        c.confirm_empty()
        for value in ('NaN', '-1', '125.1', '0.01'):
            with self.assertRaises(ValueError): c.motion('aspirate', value, 1)
        with self.assertRaises(ValueError): c.motion('dispense', 5, 1)
        result = c.motion('cycle', 5, 1)
        bodies = [body for kind, body in f.sent if kind == 5]
        self.assertEqual(bodies, [b'\x01\x01\x00\x32\x00\x00' + b'VIAFLO PC control   ' + b'\x00\x00',
                                  b'\x07\x01\x00\x32\x00\x00' + b'VIAFLO PC control   ' + b'\x00\x00'])
        self.assertEqual(result['tracked_volume_ul'], 0)

    def test_timeout_never_sends_followup_motion(self):
        c, f = self.controller(TimeoutError('Unknown outcome'))
        c.confirm_empty()
        with self.assertRaises(TimeoutError): c.motion('cycle', 5, 1)
        self.assertEqual(len([x for x in f.sent if x[0] == 5]), 1)
        self.assertIsNone(c.link)
        self.assertIsNone(c.loaded_units)
        self.assertTrue(f.closed)

    def test_busy_and_hardware_fault_prevent_motion(self):
        for state, hw in ((3, 0), (4, 0), (0, 1)):
            c, f = self.controller()
            c.loaded_units = 0
            original = f.transact
            f.transact = lambda kind, body=b'', timeout=5: packet(2, struct.pack('>HH', state, hw)) if kind == 2 else original(kind, body)
            with self.assertRaises(v.ProtocolError): c.motion('aspirate', 5, 1)
            self.assertFalse(any(k == 5 for k, _ in f.sent))


if __name__ == '__main__': unittest.main()
