import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents/skills/antigravity-delegate/scripts"
sys.path.insert(0, str(SCRIPTS))
from adapters.antigravity_cli import AntigravityCLI


class AdapterReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def help_adapter(self, help_text, exit_code=0):
        adapter = AntigravityCLI(sys.executable)
        with patch("adapters.antigravity_cli.subprocess.run", return_value=
                   subprocess.CompletedProcess([], exit_code, help_text)):
            adapter.capabilities()
        return adapter

    def test_print_only_cli_is_supported_without_optional_flags(self):
        adapter = self.help_adapter("--mode Mode (accept-edits|plan)\n--print PROMPT\n")
        adapter.validate_launch()
        argv = adapter.argv(self.root, self.root / "context", self.root / "receipt", self.root)
        self.assertTrue(any(arg.startswith("--print=") for arg in argv))
        for flag in ("--add-dir", "--log-file", "--print-timeout", "--output-format"):
            self.assertNotIn(flag, argv)

    def test_flag_prefix_and_failed_help_do_not_prove_capability(self):
        adapter = self.help_adapter("--mode Mode (accept-edits|plan)\n--print-timeout SECONDS\n--include FILE\n")
        self.assertIsNone(adapter.capabilities()["print_arg"])
        self.assertIsNone(adapter.capabilities()["interactive_arg"])
        with self.assertRaisesRegex(ValueError, "--print or -p"):
            adapter.validate_launch()
        with self.assertRaisesRegex(ValueError, "exit code 7"):
            self.help_adapter("--mode Mode (accept-edits)\n--print PROMPT", 7)

    def test_unadvertised_mode_fails_closed(self):
        adapter = self.help_adapter("--print PROMPT\n")
        with self.assertRaisesRegex(ValueError, "--mode"):
            adapter.validate_launch()

    def test_text_output_is_not_parsed_as_stream_json(self):
        adapter = self.help_adapter("--mode Mode (accept-edits, plan)\n--print PROMPT\n")
        receipt = self.root / "receipt.yaml"
        receipt.write_text("status: COMPLETE\n")
        def execute(argv, **kwargs):
            kwargs["log"].write_text("Implementation finished normally.\n")
            return {"exit_code": 0}
        with patch("adapters.antigravity_cli.run_command", side_effect=execute):
            result = adapter.launch(self.root, self.root / "context", receipt, self.root)
        self.assertEqual(result["output_format"], "TEXT")
        self.assertEqual(result["diagnostic"], "RECEIPT_PRESENT_UNVERIFIED")

    def test_probe_only_invokes_help_and_version(self):
        calls = []
        def inspect(argv, **kwargs):
            calls.append(argv[1:])
            return subprocess.CompletedProcess(argv, 0, "--mode Mode (accept-edits)\n--print PROMPT")
        with patch("adapters.antigravity_cli.subprocess.run", side_effect=inspect):
            result = AntigravityCLI(sys.executable).probe(self.root)
        self.assertTrue(result["available"])
        self.assertTrue(calls)
        self.assertTrue(all(args in (["--help"], ["--version"]) for args in calls))
        self.assertEqual(result["headless"], "UNVERIFIED")

    def test_executor_timeout_stops_real_child_before_late_write(self):
        marker = self.root / "late.txt"
        child = f"import time; from pathlib import Path; time.sleep(3); Path({str(marker)!r}).write_text('alive')"
        parent = ("import subprocess,sys,time; "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
                  "print('CHILD_STARTED',flush=True); time.sleep(30)")
        adapter = AntigravityCLI(sys.executable, ["-c", parent], timeout=1)
        result = adapter.launch(self.root, self.root / "context", self.root / "receipt", self.root)
        self.assertEqual(result["exit_code"], 124)
        self.assertTrue(result["timed_out"])
        self.assertIn("CHILD_STARTED", (self.root / "launch.log").read_text())
        time.sleep(3)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
