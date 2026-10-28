import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / ".agents/skills/antigravity-delegate/scripts"))
from process_utils import run_command, split_command


class CheckProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="check process ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_native_argument_quoting_roundtrip(self):
        args = [sys.executable, "-c", "print('hello world')", "path with spaces", 'a"b', "C:\\tail\\"]
        text = subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
        self.assertEqual(split_command(text), args)

    def test_default_argv_returns_real_output_and_exit_code(self):
        log = self.root / "check.log"
        result = run_command([sys.executable, "-c", "print('CHECK_OK'); raise SystemExit(7)"],
                             cwd=self.root, log=log, timeout=10)
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["result"], "FAIL")
        self.assertFalse(result["shell"])
        self.assertIn("CHECK_OK", log.read_text())

    def test_missing_program_is_a_recorded_failure(self):
        log = self.root / "missing.log"
        result = run_command([str(self.root / "missing-program")], cwd=self.root, log=log, timeout=5)
        self.assertEqual(result["exit_code"], 127)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("error", result)
        self.assertTrue(log.read_bytes())

    def test_invalid_command_and_implicit_shell_operators_are_rejected(self):
        for command in (" ", "x\0y", "echo first && echo second", "echo x | echo y"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    split_command(command)

    def test_timeout_stops_child_process_before_late_write(self):
        marker = self.root / "late.txt"
        child = f"import time; from pathlib import Path; time.sleep(3); Path({str(marker)!r}).write_text('alive')"
        parent = ("import subprocess,sys,time; "
                  f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
                  "print('CHILD_STARTED',p.pid,flush=True); time.sleep(30)")
        log = self.root / "timeout.log"
        result = run_command([sys.executable, "-c", parent], cwd=self.root, log=log, timeout=1)
        self.assertEqual(result["exit_code"], 124)
        self.assertTrue(result["timed_out"])
        self.assertIn("CHILD_STARTED", log.read_text())
        time.sleep(3)
        self.assertFalse(marker.exists(), "Timed-out check left its child process running")


if __name__ == "__main__":
    unittest.main()
