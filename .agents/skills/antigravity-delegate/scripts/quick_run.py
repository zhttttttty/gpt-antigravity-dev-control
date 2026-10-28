"""One isolated agy implementation and caller-supplied checks; acceptance stays with Codex."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from delegate import AntigravityCLI, save, scope_violations
from process_utils import run_command, split_command


LAUNCH_PROMPT = (
    "Implement the single request in {context}. Work only in {worktree}. "
    "The context and report paths are explicit exceptions outside the worktree: "
    "read that context, then write the small JSON executor report to {receipt}. "
    "Do not access other parent/home/scratch paths. Do not commit, switch branches, "
    "merge, push, change control files or expand scope. Stop and report BLOCKED on "
    "architecture, authentication, deployment or destructive decisions outside the request. "
    "Prefer synchronous commands. Poll actual returned handles for asynchronous work. "
    "Do not bypass denied permissions. Follow the exact report format in the context, then exit."
)
PROTECTED = [".git", ".git/**", ".ai", ".agents", ".codex", ".codex/**", ".github", ".github/**"]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout


def plan(root: Path, request: str, allow: list[str], checks: list[str],
         timeout: int, check_timeout: int, total_check_timeout: int = 900,
         shell_checks: bool = False) -> dict:
    if not request.strip():
        raise ValueError("Request must not be empty")
    if timeout <= 0 or check_timeout <= 0 or total_check_timeout <= 0:
        raise ValueError("Timeouts must be positive")
    for pattern in allow:
        normalized = pattern.replace("\\", "/")
        if not normalized or normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
            raise ValueError("--allow requires a repository-relative path pattern")
    if any(not command.strip() for command in checks):
        raise ValueError("Check commands must not be empty")
    if not shell_checks:
        for command in checks:
            if not split_command(command):
                raise ValueError("Check argv must not be empty")
    context = (
        "# Single implementation request\n\n" + request.strip()
        + "\n\nWritable patterns: " + json.dumps(allow, ensure_ascii=False)
        + "\nProtected: .git, .ai, .agents, .codex, .github, AGENTS.md, GEMINI.md."
        + "\nCaller checks (the controller runs these after you exit): "
        + json.dumps(checks, ensure_ascii=False)
        + '\nDo not commit or change branches. Write only this JSON report to the supplied report path:'
        + '\n{"status":"COMPLETE","summary":"actual outcome","notes":[]}'
        + '\nUse status BLOCKED instead if you cannot finish.'
        + "\nReport what happened; do not claim tests you did not run or independent acceptance.\n"
    )
    if len(context.encode("utf-8")) > 32_000:
        raise ValueError("Request context exceeds 32,000 UTF-8 bytes; reduce the request")
    root = Path(git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    base = git(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    return {"repository": str(root), "base_commit": base, "request": request.strip(),
            "allow": [p.replace("\\", "/") for p in allow], "check_commands": checks,
            "timeout": timeout, "check_timeout": check_timeout,
            "total_check_timeout": total_check_timeout, "shell_checks": shell_checks,
            "source_clean": not bool(git(root, "status", "--porcelain", "--untracked-files=all")),
            "context": context}


def observe(worktree: Path, base: str, branch: str, run_dir: Path, record: dict) -> None:
    tracked = git(worktree, "diff", "--name-only", "--no-renames", "-z", base, "--")
    untracked = git(worktree, "ls-files", "--others", "--exclude-standard", "-z")
    files = sorted(set(filter(None, tracked.split("\0") + untracked.split("\0"))))
    record["changed_files"] = files
    record["untracked_files"] = sorted(filter(None, untracked.split("\0")))
    record["head_commit"] = git(worktree, "rev-parse", "HEAD").strip()
    record["actual_branch"] = git(worktree, "branch", "--show-current").strip()
    diff = subprocess.run(["git", "diff", "--binary", "--no-ext-diff", "--no-renames", base, "--"],
                          cwd=worktree, capture_output=True, check=True).stdout
    (run_dir / "tracked.diff").write_bytes(diff)
    record["diff"] = str(run_dir / "tracked.diff")
    record["diff_scope"] = "tracked files only; inspect untracked_files inside worktree separately"
    record["scope_violations"] = scope_violations(files, {
        "scope": {"writable": record["allow"], "protected": PROTECTED}})
    control_names = {".git", ".ai", ".agents", ".codex", ".github", "agents.md", "gemini.md"}
    record["scope_violations"] = sorted(set(record["scope_violations"]) | {
        path for path in files if path.replace("\\", "/").split("/", 1)[0].casefold() in control_names})
    if record["head_commit"] != base or record["actual_branch"] != branch:
        raise ValueError("Executor or checks changed Git history/branch; inspect the retained worktree")
    if record["scope_violations"]:
        raise ValueError("Out-of-scope changes; inspect scope_violations and retained worktree")


def run(root: Path, request: str, *, allow=None, checks=None, timeout=1260,
        check_timeout=300, total_check_timeout=900, shell_checks=False,
        adapter=None, dry_run=False) -> dict:
    details = plan(root, request, allow or ["**"], checks or [], timeout, check_timeout,
                   total_check_timeout, shell_checks)
    if dry_run:
        return {key: value for key, value in {"status": "DRY_RUN", **details}.items() if key != "context"}
    if not details["source_clean"]:
        raise ValueError("Source checkout is dirty; commit or otherwise preserve changes before run. No uncommitted content is copied")
    root = Path(details["repository"])
    adapter = adapter or AntigravityCLI(timeout=timeout, launch_prompt=LAUNCH_PROMPT)
    adapter.validate_launch()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    run_dir = common / "agy-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    worktree, branch = run_dir / "workspace", "codex/agy-" + run_id
    started = time.monotonic()
    record = {key: value for key, value in details.items() if key != "context"}
    record.update(schema_version=1, run_id=run_id, status="PREPARING", branch=branch,
                  worktree=str(worktree), run_dir=str(run_dir), checks=[], changed_files=[],
                  review_verdict="PENDING", checks_status="NOT_RUN", usage="UNKNOWN")
    result_path = run_dir / "result.json"
    record["result_file"] = str(result_path)
    save(result_path, record)
    try:
        git(root, "worktree", "add", "-b", branch, str(worktree), details["base_commit"])
        context, report = run_dir / "context.md", run_dir / "executor.json"
        context.write_text(details["context"], encoding="utf-8")
        record["executor_report"] = str(report)
        logs = run_dir / "launch"
        logs.mkdir()
        record["status"] = "RUNNING"
        save(result_path, record)
        record["launch"] = adapter.launch(worktree, context, report, logs)
        observe(worktree, details["base_commit"], branch, run_dir, record)
        if type(record["launch"].get("exit_code")) is not int or record["launch"]["exit_code"] != 0:
            raise ValueError("agy did not exit successfully; inspect launch logs before retrying")
        if record["launch"].get("diagnostic") in {"AUTH_REQUIRED", "PERMISSION_BLOCKED", "PROCESS_FAILED", "INTERRUPTED", "FORMAT_INVALID", "EMPTY_OUTPUT"}:
            raise ValueError(f"agy reported {record['launch']['diagnostic']}; inspect launch logs")
        if report.is_symlink() or not report.is_file() or report.stat().st_size > 128_000:
            raise ValueError("Missing or oversized executor JSON report; exit 0 is not completion")
        executor = json.loads(report.read_text(encoding="utf-8"))
        if (not isinstance(executor, dict) or not isinstance(executor.get("status"), str)
                or executor["status"] not in {"COMPLETE", "BLOCKED"}
                or not isinstance(executor.get("summary"), str) or not executor["summary"].strip()):
            raise ValueError("Invalid executor report: status COMPLETE/BLOCKED and nonempty summary required")
        record["executor_summary"] = executor["summary"]
        if executor["status"] != "COMPLETE":
            raise ValueError("Executor reported BLOCKED; inspect its report")
        check_started = time.monotonic()
        for number, command in enumerate(details["check_commands"], 1):
            output = run_dir / f"check-{number}.log"
            remaining = total_check_timeout - (time.monotonic() - check_started)
            if remaining <= 0:
                result = {"command": command, "log": str(output), "exit_code": None,
                          "result": "NOT_RUN", "error": "Total check deadline exhausted"}
                output.write_text("NOT_RUN: total check deadline exhausted\n", encoding="utf-8")
            else:
                result = {"command": command, **run_command(command, cwd=worktree, log=output,
                          timeout=min(check_timeout, remaining), shell=shell_checks)}
            record["checks"].append(result)
            observe(worktree, details["base_commit"], branch, run_dir, record)
            if result.get("interrupted"):
                break
        if record["checks"]:
            record["checks_status"] = "PASS" if all(c["result"] == "PASS" for c in record["checks"]) else "FAIL"
        observe(worktree, details["base_commit"], branch, run_dir, record)
        record["status"] = "CHECK_FAILED" if record["checks_status"] == "FAIL" else "READY_FOR_REVIEW"
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        record.update(status="BLOCKED", error=str(exc) or "Interrupted; inspect the retained worktree")
        if worktree.is_dir():
            try:
                observe(worktree, details["base_commit"], branch, run_dir, record)
            except (ValueError, OSError, subprocess.SubprocessError) as observation_error:
                record["observation_error"] = str(observation_error)
    finally:
        record["checks_expected"] = len(details["check_commands"])
        if record["checks"]:
            record["checks_status"] = "PASS" if (len(record["checks"]) == record["checks_expected"]
                and all(c["result"] == "PASS" for c in record["checks"])) else "FAIL"
        if record["status"] != "READY_FOR_REVIEW":
            record["next_step"] = "Inspect logs, worktree and actual processes before retrying or cleanup; no automatic recovery"
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save(result_path, record)
    return record


def compact(record: dict) -> dict:
    if record["status"] == "DRY_RUN":
        return record
    result = {key: value for key, value in record.items() if key not in {"request", "check_commands"}}
    for key in ("changed_files", "untracked_files", "scope_violations"):
        if key in result:
            result[key + "_total"] = len(result[key])
            result[key] = result[key][:20]
    if "executor_summary" in result:
        result["executor_summary"] = result["executor_summary"][:2000]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("--allow", action="append", default=[], help="Writable relative path pattern; repeatable")
    parser.add_argument("--check", action="append", default=[], help="Caller-supplied check, parsed as argv unless --shell-checks")
    parser.add_argument("--shell-checks", action="store_true", help="Explicitly allow shell syntax in caller-supplied checks")
    parser.add_argument("--timeout", type=int, default=1260)
    parser.add_argument("--check-timeout", type=int, default=300)
    parser.add_argument("--total-check-timeout", type=int, default=900)
    parser.add_argument("--executable", default="agy")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        adapter = AntigravityCLI(args.executable, timeout=args.timeout, interactive=args.interactive,
                                 launch_prompt=LAUNCH_PROMPT)
        result = run(Path.cwd(), args.request, allow=args.allow, checks=args.check,
                     timeout=args.timeout, check_timeout=args.check_timeout,
                     total_check_timeout=args.total_check_timeout, shell_checks=args.shell_checks,
                     adapter=adapter, dry_run=args.dry_run)
        print(json.dumps(compact(result), ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"DRY_RUN", "READY_FOR_REVIEW"} else 2
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
