"""Explicit argv adapter. Never infer headless capability from --help success."""
import json
import shutil
import subprocess
import sys
import re
import time
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
            "Use absolute paths for native file creation/edit tools, but for searches use relative paths in worktree cwd (never absolute Windows drive paths in grep_search). "
            "Do not access home, scratch or parent directories. "
        )
        if self.mode == "plan":
            prompt += (
                "This is a read-only review. Do not create, edit, delete, commit, merge, or push files. "
                "Inspect the requested scope and write only the final report to stdout; do not narrate progress. "
                "Treat existing tests as evidence, not proof: challenge each named correctness, validation, "
                "immutability, or security invariant with at least one adversarial counterexample when applicable, "
                "including public constructors and language/runtime escape hatches. Report uncertainty instead of PASS. "
            )
        else:
            prompt += (
                "Implement only the contract. Use native file creation/edit tools (nonempty content), "
                "not multiline shell or encoded Python commands to write files. "
                "Prefer synchronous bounded commands and relative-path search in worktree cwd on Windows. "
                "Print-mode command workflow uses actual returned handle; if run_command returns a TaskId, "
                "immediately poll manage_task status for that exact TaskId until DONE/FAILED; "
                "if CommandId use command_status. Do not use schedule, timers, or passively narrate waiting. "
                "Read returned actual stdout/stderr; do not claim missing exit codes. "
                "Before COMPLETE, exercise negative or adversarial cases for contract invariants that ordinary happy-path tests may miss. "
                "Run focused checks needed while coding, but do not spend the model session rerunning the full contract matrix; "
                "the controller verify phase owns authoritative command execution. Commit implementation files only. "
                "Fill actual executor identity and acceptance evidence in {receipt}, set status IMPLEMENTED, then STOP. "
                "Do not invent command results or workspace hashes; controller verify fills those fields. "
                "Do not read/write QA or review files, expand scope, merge, push, or claim unexecuted tests passed. "
            )
        prompt += "If a permission is denied, report the blocker; do not search alternative directories."
        if self.args is not None:
            args = self.args
        else:
            capabilities = self.capabilities()
            mode_args = ["--mode", self.mode] if capabilities["mode"] else []
            access_args = ["--dangerously-skip-permissions"] if self.full_access else []
            format_args = ["--output-format", "stream-json"] if (not self.interactive and capabilities.get("stream_json")) else []
            if self.interactive:
                args = [
                    "--add-dir", "{worktree}", "--log-file", str(logs / "agy.log"),
                    *mode_args, *access_args, capabilities["interactive_arg"], prompt,
                ]
            else:
                print_timeout_seconds = max(1, self.timeout - 5)
                args = [
                    "--add-dir", "{worktree}", "--log-file", str(logs / "agy.log"),
                    *format_args,
                    *mode_args, *access_args, "--print-timeout", f"{print_timeout_seconds}s",
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
            "stream_json": "--output-format" in help_text and "stream-json" in help_text,
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
        started = time.monotonic()
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
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["output_bytes"] = path.stat().st_size if path.is_file() else 0
        if not self.interactive and self.args is None and path.is_file():
            try:
                events = parse_stream_events(path.read_text(encoding="utf-8", errors="replace"))
                if events:
                    events_path = logs / "events.json"
                    events_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                    result["stream_events"] = str(events_path)
                    result["output_format"] = (
                        "INVALID" if any(event.get("status") in {"MALFORMED", "MIXED_OUTPUT"} for event in events)
                        else "VALID"
                    )
                else:
                    result["stream_events"] = "EMPTY_OR_UNSUPPORTED"
                    result["output_format"] = "EMPTY"
            except Exception:
                result["stream_events"] = "PARSE_ERROR"
                result["output_format"] = "INVALID"
        else:
            result["stream_events"] = "NOT_APPLICABLE" if (self.interactive or self.args is not None) else "LOG_MISSING"
            result["output_format"] = "NOT_APPLICABLE" if (self.interactive or self.args is not None) else "MISSING"
        if "diagnostic" not in result:
            base_diagnostic = diagnose(receipt, [path, logs / "agy.log"])
            if result.get("output_format") == "INVALID":
                result["secondary_diagnostic"] = "FORMAT_INVALID"
                result["diagnostic"] = (
                    base_diagnostic
                    if base_diagnostic in {"PERMISSION_BLOCKED", "EMPTY_OUTPUT", "AUTH_REQUIRED"}
                    else "FORMAT_INVALID"
                )
            else:
                result["diagnostic"] = base_diagnostic
        return result


def parse_stream_events(log_content):
    """Parse NDJSON stream-json output; capture tool start/completion, handle, result, timestamps.
    Do not claim exit code when unavailable (unknown is UNKNOWN).
    Handle malformed or truncated lines defensively.
    """
    events = []
    lines = log_content.splitlines() if isinstance(log_content, str) else log_content
    for line in lines:
        line_str = line.decode("utf-8", errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
        line_str = line_str.strip()
        if not line_str:
            continue
        if not line_str.startswith("{"):
            events.append({"event": "unexpected_text", "raw": line_str[:200], "status": "MIXED_OUTPUT"})
            continue
        try:
            payload = json.loads(line_str)
        except (json.JSONDecodeError, ValueError):
            events.append({"event": "malformed", "raw": line_str[:200], "status": "MALFORMED"})
            continue

        if not isinstance(payload, dict):
            continue

        event_name = payload.get("event")
        if event_name == "step_update":
            step = payload.get("step_update")
            if not isinstance(step, dict):
                events.append({"event": "malformed", "raw": line_str[:200], "status": "MALFORMED"})
                continue
            step_type = step.get("step_type")
            if step_type == "tool":
                state = step.get("state")
                tool_info = step.get("tool_info")
                if tool_info is not None and not isinstance(tool_info, dict):
                    events.append({"event": "malformed", "raw": line_str[:200], "status": "MALFORMED"})
                    continue
                if not isinstance(tool_info, dict):
                    tool_info = {}
                tool_name = step.get("tool_name") or tool_info.get("name")
                params = tool_info.get("parameters") or {}
                if not isinstance(params, dict):
                    params = {}

                handle = None
                raw_handle = params.get("TaskId") or params.get("task_id") or params.get("CommandId") or params.get("command_id")
                if isinstance(raw_handle, str) and raw_handle.strip():
                    handle = raw_handle.strip()

                output_data = None
                error_data = None
                if isinstance(tool_info, dict):
                    output_data = tool_info.get("output")
                    if output_data is None:
                        output_data = tool_info.get("result")
                    error_data = tool_info.get("error")
                if output_data is None and isinstance(step, dict):
                    output_data = step.get("result")

                result_data = error_data if state == "ERROR" else output_data

                if not handle and isinstance(output_data, dict):
                    raw_h = output_data.get("TaskId") or output_data.get("task_id") or output_data.get("CommandId") or output_data.get("command_id")
                    if isinstance(raw_h, str) and raw_h.strip():
                        handle = raw_h.strip()
                elif not handle and isinstance(output_data, str):
                    match = re.search(r"(?:task id[:=\s\"']+|TaskId[:=\s\"']+)([a-zA-Z0-9_/.-]+)", output_data, re.IGNORECASE)
                    if match:
                        handle = match.group(1)
                    else:
                        match_cmd = re.search(r"(?:command id[:=\s\"']+|CommandId[:=\s\"']+)([a-zA-Z0-9_/.-]+)", output_data, re.IGNORECASE)
                        if match_cmd:
                            handle = match_cmd.group(1)

                timestamp = (
                    step.get("timestamp")
                    or step.get("created_at")
                    or payload.get("timestamp")
                    or (tool_info.get("timestamp") if isinstance(tool_info, dict) else None)
                    or "UNKNOWN"
                )

                event_record = {
                    "event": "tool_start" if state == "ACTIVE" else "tool_completion",
                    "tool_name": tool_name,
                    "state": state,
                    "handle": handle,
                    "output": output_data,
                    "result": result_data,
                    "step_index": step.get("step_index"),
                    "timestamp": timestamp,
                    "duration_seconds": step.get("duration_seconds"),
                    "exit_code": None,
                }
                events.append(event_record)
        elif event_name == "result":
            res = payload.get("result")
            if res is not None and not isinstance(res, dict):
                events.append({"event": "malformed", "raw": line_str[:200], "status": "MALFORMED"})
                continue
            if not isinstance(res, dict):
                res = {}
            res_timestamp = res.get("timestamp") or res.get("created_at") or payload.get("timestamp") or "UNKNOWN"
            events.append({
                "event": "session_result",
                "status": res.get("status"),
                "timestamp": res_timestamp,
                "duration_seconds": res.get("duration_seconds"),
            })
    return events


def diagnose_tool_handle(handle_or_output):
    """Diagnose command handle or output: TaskId polled via manage_task status,
    CommandId via command_status. Passive waiting/schedule/timers and unknown formats
    are preserved as blockers.
    """
    if isinstance(handle_or_output, dict):
        if "TaskId" in handle_or_output or "task_id" in handle_or_output:
            tid = handle_or_output.get("TaskId") if "TaskId" in handle_or_output else handle_or_output.get("task_id")
            if isinstance(tid, str) and tid.strip():
                return {
                    "status": "VALID",
                    "handle_type": "task_id",
                    "handle": tid.strip(),
                    "poll_tool": "manage_task",
                    "poll_action": "status",
                }
            return {
                "status": "BLOCKED",
                "handle_type": "task_id",
                "error": f"Invalid TaskId: {tid!r}; must be nonempty string",
            }
        if "CommandId" in handle_or_output or "command_id" in handle_or_output:
            cid = handle_or_output.get("CommandId") if "CommandId" in handle_or_output else handle_or_output.get("command_id")
            if isinstance(cid, str) and cid.strip():
                return {
                    "status": "VALID",
                    "handle_type": "command_id",
                    "handle": cid.strip(),
                    "poll_tool": "command_status",
                }
            return {
                "status": "BLOCKED",
                "handle_type": "command_id",
                "error": f"Invalid CommandId: {cid!r}; must be nonempty string",
            }
        if handle_or_output.get("exit_code") is not None:
            code = handle_or_output["exit_code"]
            if type(code) is int:
                return {
                    "status": "COMPLETED",
                    "handle_type": "synchronous",
                    "exit_code": code,
                }
            return {
                "status": "BLOCKED",
                "handle_type": "synchronous",
                "error": f"Invalid exit_code: {code!r}; must be integer",
            }
        return {
            "status": "BLOCKED",
            "handle_type": "unknown",
            "error": f"Unknown structured handle format: {handle_or_output}",
        }

    if not isinstance(handle_or_output, str):
        if handle_or_output is None:
            return {"status": "BLOCKED", "handle_type": "empty", "error": "Empty command handle/output"}
        return {
            "status": "BLOCKED",
            "handle_type": "malformed",
            "error": f"Malformed handle/output type: {type(handle_or_output).__name__}",
        }

    text = handle_or_output.strip()
    if not text:
        return {"status": "BLOCKED", "handle_type": "empty", "error": "Empty command handle/output"}

    passive_markers = [
        "schedule",
        "timer",
        "passively narrat",
        "waiting for background",
        "wait for background",
        "still running, waiting",
        "sleep ",
    ]
    lower_text = text.lower()
    for marker in passive_markers:
        if marker in lower_text:
            return {
                "status": "BLOCKED",
                "handle_type": "passive_waiting",
                "error": f"Passive narration or wait timer/schedule detected ({marker}); must poll actual tool handle",
            }

    task_match = re.search(r"(?:task id[:=\s\"']+|TaskId[:=\s\"']+)([a-zA-Z0-9_/.-]+)", text, re.IGNORECASE)
    if task_match:
        val = task_match.group(1).strip()
        if val and val.lower() not in {"null", "none", "empty"}:
            return {
                "status": "VALID",
                "handle_type": "task_id",
                "handle": val,
                "poll_tool": "manage_task",
                "poll_action": "status",
            }
        return {
            "status": "BLOCKED",
            "handle_type": "task_id",
            "error": f"Null/empty TaskId in text: {val!r}",
        }

    cmd_match = re.search(r"(?:command id[:=\s\"']+|CommandId[:=\s\"']+)([a-zA-Z0-9_/.-]+)", text, re.IGNORECASE)
    if cmd_match:
        val = cmd_match.group(1).strip()
        if val and val.lower() not in {"null", "none", "empty"}:
            return {
                "status": "VALID",
                "handle_type": "command_id",
                "handle": val,
                "poll_tool": "command_status",
            }
        return {
            "status": "BLOCKED",
            "handle_type": "command_id",
            "error": f"Null/empty CommandId in text: {val!r}",
        }

    exit_match = re.search(r"(?:exited with code\s+|returncode\s*[:=]\s*)(\d+)", text, re.IGNORECASE)
    if exit_match:
        return {
            "status": "COMPLETED",
            "handle_type": "synchronous",
            "exit_code": int(exit_match.group(1)),
        }

    return {
        "status": "BLOCKED",
        "handle_type": "unknown",
        "error": f"Unknown command handle format: {text[:100]}",
    }


def diagnose(receipt, logs):
    """Bounded log inspection; return categories, never raw account/credential text."""
    text = ""
    for path in logs:
        if path.is_file():
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 262144))
                text += stream.read(262144).decode("utf-8", errors="replace").lower()
    permission_markers = (
        "soft-denying tool confirmation",
        "headless mode cannot prompt",
        "permission that headless mode cannot prompt for",
        "auto-denied",
        "add an allow-rule under permissions.allow",
    )
    if any(marker in text for marker in permission_markers):
        return "PERMISSION_BLOCKED"
    if "no output produced" in text:
        return "EMPTY_OUTPUT"

    login_warn_markers = ("you are not logged into antigravity",)
    auth_success_markers = (
        "silent auth succeeded",
        "authorization succeeded",
        "login succeeded",
        "login successful",
        "successfully logged in",
        "authenticated successfully",
    )
    warn_pos = max((text.rfind(m) for m in login_warn_markers), default=-1)
    auth_pos = max((text.rfind(m) for m in auth_success_markers), default=-1)
    has_later_auth = auth_pos > warn_pos if warn_pos != -1 else False

    receipt_valid = False
    receipt_category = "NO_COMPLETION_EVIDENCE"
    try:
        if receipt.stat().st_size > 128000:
            receipt_category = "RECEIPT_INVALID"
        else:
            value = yaml.safe_load(receipt.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                receipt_category = "RECEIPT_INVALID"
            elif value.get("status") in {"COMPLETE", "BLOCKED", "FAILED"}:
                receipt_valid = True
                receipt_category = "RECEIPT_PRESENT_UNVERIFIED"
            else:
                receipt_category = "NO_COMPLETION_EVIDENCE"
    except FileNotFoundError:
        receipt_category = "RECEIPT_MISSING"
    except (OSError, ValueError, yaml.YAMLError):
        receipt_category = "RECEIPT_INVALID"

    if warn_pos != -1 and not (has_later_auth and receipt_valid):
        # If there is later auth but receipt is missing/invalid, diagnose will report the receipt issue.
        # But if there is no later auth, it remains a current true auth failure.
        if not has_later_auth:
            return "AUTH_REQUIRED"

    return receipt_category
