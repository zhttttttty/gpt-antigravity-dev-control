"""Shared noninteractive check execution for daily runs and contract verification."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import signal
import subprocess
import time


def _checked_argv(values: list[str]) -> list[str]:
    if any(value in {"&&", "||", "|", ";", "&", ">", ">>", "<", "2>", "2>&1"} for value in values):
        raise ValueError("Shell operators require an explicit shell check (--shell-checks for run)")
    return values


def split_command(command: str) -> list[str]:
    if not command.strip() or "\0" in command:
        raise ValueError("Check command must be nonempty and contain no NUL")
    if os.name != "nt":
        return _checked_argv(shlex.split(command, posix=True))
    # Match native Windows argv quoting; shlex would corrupt unquoted drive paths.
    import ctypes
    from ctypes import wintypes
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    free = ctypes.windll.kernel32.LocalFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = ctypes.c_void_p
    count = ctypes.c_int()
    values = parse(command, ctypes.byref(count))
    if not values:
        raise ctypes.WinError()
    try:
        return _checked_argv([values[index] for index in range(count.value)])
    finally:
        free(ctypes.cast(values, ctypes.c_void_p))


def terminate_process_tree(process: subprocess.Popen) -> None:
    """Best-effort bounded teardown of a process group created by this module."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           check=False, capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        # Still stop the process we own if platform-wide tree teardown failed.
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_command(command: str | list[str], *, cwd: Path, log: Path,
                timeout: float, shell: bool = False) -> dict:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Check timeout must be positive")
    if shell:
        if not isinstance(command, str) or not command.strip() or "\0" in command:
            raise ValueError("Shell checks require a nonempty command string")
        argv = command
    else:
        argv = split_command(command) if isinstance(command, str) else command
        if not argv or not all(isinstance(arg, str) and "\0" not in arg for arg in argv):
            raise ValueError("Check argv must be a nonempty string list")
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
               else {"start_new_session": True})
    started = time.monotonic()
    result = {"exit_code": None, "result": "FAIL", "log": str(log), "shell": shell}
    with log.open("wb") as stream:
        try:
            with subprocess.Popen(argv, cwd=cwd, shell=shell, stdin=subprocess.DEVNULL,
                                  stdout=stream, stderr=subprocess.STDOUT, **options) as process:
                try:
                    result["exit_code"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    terminate_process_tree(process)
                    stream.write(b"\nTIMEOUT\n")
                    result.update(exit_code=124, timed_out=True, error="Check timed out; process-tree teardown attempted")
                except KeyboardInterrupt:
                    terminate_process_tree(process)
                    stream.write(b"\nINTERRUPTED\n")
                    result.update(exit_code=130, interrupted=True, error="Check interrupted; process-tree teardown attempted")
        except OSError as exc:
            result.update(exit_code=127, error=str(exc))
            stream.write((str(exc) + "\n").encode("utf-8", errors="replace"))
    result["result"] = "PASS" if result["exit_code"] == 0 else "FAIL"
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result
