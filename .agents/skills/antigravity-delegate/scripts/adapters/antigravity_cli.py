"""Explicit argv adapter. Never infer headless capability from --help success."""
import shutil
import subprocess
import sys
import re
from pathlib import Path

import yaml


class AntigravityCLI:
    def __init__(self, executable="agy", args=None, timeout=1260, interactive=False, full_access=False, mode="accept-edits"):
        self.executable = executable
        self.args = args
        self.timeout = timeout
        self.interactive = interactive
        self.full_access = full_access
        self.mode = mode
        self._capabilities = None

    def validate_launch(self):
        self.resolve()
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.interactive and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise ValueError("Interactive launch requires a real terminal/PTY; do not redirect stdin/stdout")
        if self.interactive and self.args is not None:
            raise ValueError("Interactive launch uses managed arguments; --args-file is print-mode only")
        if self.args is None:
            capabilities = self.capabilities()
            if self.full_access and not capabilities["permission_bypass"]:
                raise ValueError("CLI does not advertise --dangerously-skip-permissions; refuse full-access launch")
            if self.mode not in capabilities["mode_values"]:
                raise ValueError(
                    f"CLI does not advertise --mode {self.mode}; supported modes: "
                    f"{', '.join(capabilities['mode_values']) or 'unknown'}"
                )

    def argv(self, worktree, context, receipt, logs):
        prompt = (
            "Work ONLY inside {worktree}. Read the absolute task context file {context}. "
            "Use absolute paths for file/search tools and this worktree as command cwd. "
            "Do not access home, scratch or parent directories. "
        )
        if self.mode == "plan":
            prompt += (
                "This is a read-only review. Do not create, edit, delete, commit, merge, or push files. "
                "Inspect the requested scope and write only the final report to stdout. "
            )
        else:
            prompt += (
                "Implement only the contract. Use native file creation/edit tools (nonempty content), "
                "not multiline shell or encoded Python commands to write files. Run the required test "
                "commands and save actual test output locally. Commit implementation files only. "
                "Fill the executor receipt at {receipt} using native file editing, then STOP. "
                "Do not read/write QA or review files, expand scope, merge, push, or claim unexecuted tests passed. "
            )
        prompt += "If a permission is denied, report the blocker; do not search alternative directories."
        if self.args is not None:
            args = self.args
        else:
            capabilities = self.capabilities()
            mode_args = ["--mode", self.mode] if capabilities["mode"] else []
            access_args = ["--dangerously-skip-permissions"] if self.full_access else []
            if self.interactive:
                args = [
                    "--add-dir", "{worktree}", "--log-file", str(logs / "agy.log"),
                    *mode_args, *access_args, capabilities["interactive_arg"], prompt,
                ]
            else:
                args = [
                    "--add-dir", "{worktree}", "--log-file", str(logs / "agy.log"),
                    *mode_args, *access_args, "--print-timeout", "20m",
                    f"{capabilities['print_arg']}={prompt}",
                ]
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

    def capabilities(self):
        if self._capabilities is not None:
            return self._capabilities
        executable = self.resolve()
        try:
            completed = subprocess.run(
                [executable, "--help"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=15,
                stdin=subprocess.DEVNULL, shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError(f"Unable to inspect agy capabilities: {exc}") from exc
        help_text = completed.stdout or ""
        mode_match = re.search(r"--mode\s+.*?\(([^)]*)\)", help_text, re.IGNORECASE | re.DOTALL)
        mode_values = []
        if mode_match:
            mode_values = [value.strip() for value in mode_match.group(1).split("|") if value.strip()]
            if len(mode_values) == 1:
                mode_values = [value.strip() for value in mode_match.group(1).split(",") if value.strip()]
        self._capabilities = {
            "help_exit_code": completed.returncode,
            "permission_bypass": "--dangerously-skip-permissions" in help_text,
            "sandbox": "--sandbox" in help_text,
            "mode": "--mode" in help_text,
            "mode_values": mode_values,
            "print_arg": "--print" if "--print" in help_text else "-p" if "-p" in help_text else None,
            "interactive_arg": "--prompt-interactive" if "--prompt-interactive" in help_text else "-i" if "-i" in help_text else None,
        }
        if not self._capabilities["print_arg"]:
            raise ValueError("CLI does not advertise --print or -p")
        if not self._capabilities["interactive_arg"]:
            raise ValueError("CLI does not advertise interactive prompt mode")
        return self._capabilities

    def probe(self, logs):
        logs.mkdir(parents=True, exist_ok=True)
        try:
            executable = self.resolve()
        except ValueError as exc:
            return {"available": False, "error": str(exc), "login": "UNKNOWN",
                    "headless": "UNVERIFIED"}
        results = {}
        for name, probe_args in (("version", ["--version"]), ("help", ["--help"])):
            path = logs / f"{name}.log"
            with path.open("wb") as output:
                try:
                    cp = subprocess.run([executable, *probe_args], stdout=output,
                                        stderr=subprocess.STDOUT, timeout=15,
                                        stdin=subprocess.DEVNULL, shell=False)
                    results[name] = {"exit_code": cp.returncode, "log": str(path)}
                except (OSError, subprocess.TimeoutExpired) as exc:
                    results[name] = {"error": str(exc), "log": str(path)}
        agent_probes = {}
        for name, probe_args in (("agent", ["agent"]), ("agents", ["agents"]), ("agent_list", ["agent", "list"])):
            path = logs / f"{name}.log"
            try:
                with path.open("wb") as output:
                    cp = subprocess.run([executable, *probe_args], stdout=output,
                                        stderr=subprocess.STDOUT, timeout=15,
                                        stdin=subprocess.DEVNULL, shell=False)
                agent_probes[name] = {"exit_code": cp.returncode, "log": str(path)}
            except (OSError, subprocess.TimeoutExpired) as exc:
                agent_probes[name] = {"error": str(exc), "log": str(path)}
        try:
            capabilities = self.capabilities()
        except ValueError as exc:
            capabilities = {"error": str(exc)}
        return {"available": True, "executable": executable, "probes": results,
                "agent_probes": agent_probes, "capabilities": capabilities,
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
