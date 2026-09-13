"""Offline command-policy checks. Real mathematics is in examples/exact_checks.py."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sage import build_command, parser


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def command(self, *args):
        a = parser().parse_args(['--workdir', str(self.work), *args])
        return build_command(a, 'sha256:test', 'sage-local-test')

    def test_offline_readonly_eval_uses_no_shell(self):
        expression = 'print(2^10); print("$(do-not-execute)")'
        c = self.command('eval', expression)
        self.assertIn('--pull=never', c)
        self.assertIn('--network=none', c)
        self.assertNotIn('--publish', c)
        self.assertIn(f'type=bind,src={self.work},dst=/work,readonly', c)
        self.assertEqual(c[-2:], ['-c', expression])

    def test_python_and_sage_use_correct_runtimes(self):
        for suffix, expected in (('.py', ['-python', '/work/demo.py']),
                                 ('.sage', ['/work/demo.sage'])):
            (self.work / ('demo' + suffix)).touch()
            c = self.command('run', 'demo' + suffix, '--example', 'value')
            self.assertEqual(c[-len(expected)-2:], [*expected, '--example', 'value'])

    def test_script_escape_is_rejected(self):
        (self.work / 'escape.py').symlink_to(Path(__file__))
        for path in ('../escape.py', 'escape.py'):
            with self.assertRaises(ValueError):
                self.command('run', path)

    def test_jupyter_auth_and_loopback(self):
        with self.assertRaises(ValueError):
            self.command('jupyter')
        c = self.command('--write', '--port', '18889', 'jupyter')
        self.assertIn('127.0.0.1:18889:8888', c)
        self.assertNotIn('--network=none', c)
        self.assertFalse(any('token=' in part or 'password=' in part for part in c))
        self.assertNotIn('-d', c)
        self.assertIn(f'type=bind,src={self.work},dst=/work', c)

    def test_doctor_mounts_no_repository(self):
        c = self.command('doctor')
        self.assertNotIn('--mount', c)
        self.assertIn('--network=none', c)

    def test_invalid_settings_fail_before_docker(self):
        for args in (('--port', '0', 'doctor'), ('--timeout', '0', 'doctor'),
                     ('run', 'missing.py')):
            with self.assertRaises(ValueError):
                self.command(*args)


if __name__ == '__main__':
    unittest.main()
