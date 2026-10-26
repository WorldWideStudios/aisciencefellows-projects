import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from tools.viaflo import cli, transport
from test_viaflo_pc_control import Fake


class ShellTests(unittest.TestCase):
    def run_shell(self, commands, fake=None):
        fake = fake or Fake()
        with patch.object(transport, 'Link', return_value=fake), \
             patch('builtins.input', side_effect=commands), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = cli.main(['shell', '--address', '00-16-a4-4c-9a-ac'])
        return result, fake

    def test_shell_requires_empty_and_preserves_volume_across_commands(self):
        result, fake = self.run_shell(['aspirate 5', 'confirm-empty', 'aspirate 5',
                                       'dispense 6', 'dispense 5', 'quit'])
        self.assertEqual(result, 0)
        actions = [body for kind, body in fake.sent if kind == 5]
        self.assertEqual([body[0] for body in actions], [1, 7])
        self.assertTrue(fake.closed)

    def test_failure_exits_before_next_command(self):
        result, fake = self.run_shell(['confirm-empty', 'cycle 5', 'aspirate 5'],
                                      Fake(TimeoutError('unknown outcome')))
        self.assertEqual(result, 1)
        self.assertEqual(sum(kind == 5 for kind, _ in fake.sent), 1)
        self.assertTrue(fake.closed)

    def test_eof_and_interrupt_close(self):
        for exception, expected in ((EOFError(), 0), (KeyboardInterrupt(), 130)):
            result, fake = self.run_shell([exception])
            self.assertEqual(result, expected)
            self.assertTrue(fake.closed)

    def test_status_is_read_only(self):
        fake = Fake()
        with patch.object(transport, 'Link', return_value=fake), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['status', '--address', '00-16-a4-4c-9a-ac']), 0)
        self.assertEqual([kind for kind, _ in fake.sent], [1, 2])
        self.assertTrue(fake.closed)

    def test_unknown_identity_rejected_before_motion(self):
        fake = Fake()
        original = fake.transact
        fake.transact = lambda kind, *a, **kw: bytes(20) if kind == 1 else original(kind, *a, **kw)
        result, fake = self.run_shell(['confirm-empty', 'aspirate 5'], fake)
        self.assertEqual(result, 1)
        self.assertFalse(any(kind == 5 for kind, _ in fake.sent))
        self.assertTrue(fake.closed)
