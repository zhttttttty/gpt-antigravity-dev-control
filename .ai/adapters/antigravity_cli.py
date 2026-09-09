"""Explicit argv adapter. Never infer headless capability from --help success."""
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


class AntigravityCLI:
    def __init__(self, executable="agy", args=None, timeout=1260, interactive=False, full_access=False):
        self.executable = executable
        self.args = args
        self.timeout = timeout
        self.interactive = interactive
        self.full_access = full_access

    def validate_launch(self):
        self.resolve()
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.interactive and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise ValueError("Interactive launch requires a real terminal/PTY; do not redirect stdin/stdout")
        if self.interactive and self.args is not None:
            raise ValueError("Interactive launch uses managed arguments; --args-file is print-mode only")

    def argv(self, worktree, context, receipt, logs):
        prompt = (
            "Work ONLY inside {worktree}. Read the absolute task context file {context}. "
            "Use absolute paths for file/search tools and this worktree as command cwd. "
            "Do not access home, scratch or parent directories. Implement only the contract. "
            "Use native file creation/edit tools (nonempty content), not multiline shell or encoded Python commands to write files. "
            "Run the required test commands and save actual test output locally. Commit implementation files only. "
            "Fill the executor receipt at {receipt} using native file editing, then STOP. "
            "Do not read/write QA or review files, expand scope, merge, push, or claim unexecuted tests passed. "
            "If a permission is denied, report the blocker; do not search alternative directories.")
        args = self.args if self.args is not None else [
            "--add-dir", "{worktree}", "--log-file", str(logs / "agy.log"),
            *(["--dangerously-skip-permissions"] if self.full_access else []),
            *(["-i", prompt] if self.interactive else ["--print-timeout", "20m", "-p", prompt])]
        if not isinstance(args, list) or not args or not all(isinstance(x, str) for x in args):
            raise ValueError("Configure a non-empty argv JSON list after inspecting CLI help")
        values = {"worktree": str(worktree), "context": str(context), "receipt": str(receipt)}
        return [self.resolve()] + [arg.format_map(values) for arg in args]

    def resolve(self):
        found = shutil.which(self.executable)
        if not found:
            raise ValueError(f"Executable not found: {self.executable}; provide --executable (Windows guide: %LOCALAPPDATA%/agy/bin/agy.exe)")
        # Avoid Windows batch-shell argument expansion. Point at a native binary
        # or a native interpreter with a script as an explicit argv element.
        if Path(found).suffix.lower() in {".cmd", ".bat"}:
            raise ValueError("Use a native executable, not a batch wrapper")
        return str(Path(found).resolve())

    def probe(self, logs):
        logs.mkdir(parents=True, exist_ok=True)
        try:
            executable = self.resolve()
        except ValueError as exc:
            return {"available": False, "error": str(exc), "login": "UNKNOWN",
                    "headless": "UNVERIFIED"}
        results = {}
        for name in ("version", "help"):
            path = logs / f"{name}.log"
            with path.open("wb") as output:
                try:
                    cp = subprocess.run([executable, "--version" if name == "version" else "help"], stdout=output,
                                        stderr=subprocess.STDOUT, timeout=15,
                                        stdin=subprocess.DEVNULL, shell=False)
                    results[name] = {"exit_code": cp.returncode, "log": str(path)}
                except (OSError, subprocess.TimeoutExpired) as exc:
                    results[name] = {"error": str(exc), "log": str(path)}
        return {"available": True, "executable": executable, "probes": results,
                "login": "UNKNOWN", "headless": "UNVERIFIED"}

    def launch(self, worktree, context, receipt, logs):
        self.validate_launch()
        argv = self.argv(worktree, context, receipt, logs)
        path = logs / "launch.log"
        result = {"exit_code": None, "log": str(path), "cli_log": str(logs / "agy.log"),
                  "mode": "interactive" if self.interactive else "print", "completion": "UNKNOWN"}
        with path.open("wb") as output:
            try:
                if self.interactive:
                    output.write(b"Interactive terminal output is not captured; see agy.log.\n")
                    cp = subprocess.run(argv, cwd=worktree, shell=False, timeout=self.timeout)
                else:
                    cp = subprocess.run(argv, cwd=worktree, stdout=output,
                                        stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                        shell=False, timeout=self.timeout)
                result["exit_code"] = cp.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                result.update(error=str(exc), diagnostic="PROCESS_FAILED")
            except KeyboardInterrupt:
                result.update(error="Interactive session interrupted; inspect worktree before recovery",
                              diagnostic="INTERRUPTED")
        if "diagnostic" not in result:
            result["diagnostic"] = diagnose(receipt, [path, logs / "agy.log"])
        return result


def diagnose(receipt, logs):
    """Bounded log inspection; return categories, never raw account/credential text."""
    text = ""
    for path in logs:
        if path.is_file():
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 262144))
                text += stream.read(262144).decode("utf-8", errors="replace").lower()
    if "soft-denying tool confirmation" in text:
        return "PERMISSION_BLOCKED"
    if "you are not logged into antigravity" in text and "silent auth succeeded" not in text:
        return "AUTH_REQUIRED"
    try:
        if receipt.stat().st_size > 128000:
            return "RECEIPT_INVALID"
        value = yaml.safe_load(receipt.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "RECEIPT_MISSING"
    except (OSError, ValueError, yaml.YAMLError):
        return "RECEIPT_INVALID"
    if not isinstance(value, dict):
        return "RECEIPT_INVALID"
    if value.get("status") in {"COMPLETE", "BLOCKED", "FAILED"}:
        return "RECEIPT_PRESENT_UNVERIFIED"
    return "NO_COMPLETION_EVIDENCE"
