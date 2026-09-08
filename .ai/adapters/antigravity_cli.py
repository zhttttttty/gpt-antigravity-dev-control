"""Explicit argv adapter. Never infer headless capability from --help success."""
import shutil
import subprocess
from pathlib import Path


class AntigravityCLI:
    def __init__(self, executable="agy", args=None, timeout=1260):
        self.executable = executable
        self.args = args
        self.timeout = timeout

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
        args = self.args if self.args is not None else [
            "--print-timeout", "20m", "-p",
            "Read {context}. Implement only that task in the current worktree {worktree}. "
            "Run required tests, commit implementation changes, and write the V2 executor receipt to {receipt}. "
            "Do not merge, push, change the contract, or claim unexecuted tests passed."]
        if not isinstance(args, list) or not args or not all(isinstance(x, str) for x in args):
            raise ValueError("Configure a non-empty argv JSON list after inspecting CLI help")
        values = {"worktree": str(worktree), "context": str(context), "receipt": str(receipt)}
        argv = [self.resolve()] + [arg.format_map(values) for arg in args]
        path = logs / "launch.log"
        with path.open("wb") as output:
            try:
                cp = subprocess.run(argv, cwd=worktree, stdout=output,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    shell=False, timeout=self.timeout)
                return {"exit_code": cp.returncode, "log": str(path),
                        "completion": "UNKNOWN"}
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {"exit_code": None, "error": str(exc), "log": str(path),
                        "completion": "UNKNOWN"}
