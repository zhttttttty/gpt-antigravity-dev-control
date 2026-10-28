"""Check repository configuration agreement without launching providers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tomllib

import yaml


NATIVE_ROLES = ("explorer", "worker", "tester", "researcher", "reviewer")
INHERITED_SETTINGS = ("sandbox_mode", "approval_policy", "model_provider", "mcp_servers")


def validate(root: Path) -> list[str]:
    errors: list[str] = []

    def read(relative: str) -> dict:
        try:
            text = (root / relative).read_text(encoding="utf-8")
            data = tomllib.loads(text) if relative.endswith(".toml") else yaml.safe_load(text)
            if not isinstance(data, dict):
                raise ValueError("expected a mapping")
            return data
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: {exc}")
            return {}

    def value(data: dict, *keys: str):
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def same(label: str, actual, expected):
        if actual is None or expected is None or actual != expected:
            errors.append(f"{label}: expected {expected!r}, got {actual!r}")

    def positive(label: str, item):
        if type(item) is not int or item < 1:
            errors.append(f"{label}: expected a positive integer, got {item!r}")
            return False
        return True

    canonical = read(".ai/config.yaml")
    config = read(".codex/config.toml")
    roles = {name: read(f".codex/agents/{name}.toml") for name in NATIVE_ROLES}
    if errors:
        # Report missing/malformed inputs once instead of cascading None/None
        # comparisons that hide the actionable file errors.
        return errors
    policy = value(canonical, "orchestration") or {}
    for role in ("architect", "planner"):
        same(f"root model / {role}", config.get("model"), value(canonical, "roles", role, "preferred_model"))
        same(f"root effort / {role}", config.get("model_reasoning_effort"), value(canonical, "roles", role, "reasoning_effort"))
    same("native enabled", value(config, "agents", "enabled"), True)
    same("native model", value(config, "agents", "default_subagent_model"), value(policy, "native_execution_model"))
    same("native effort", value(config, "agents", "default_subagent_reasoning_effort"), value(policy, "native_execution_effort"))
    native_limit = value(policy, "native_subagent_limit")
    combined_limit = value(policy, "combined_execution_limit")
    same("native limit", value(config, "agents", "max_concurrent_threads_per_session"), native_limit)
    limits_valid = [positive("native limit", native_limit), positive("combined limit", combined_limit)]
    if all(limits_valid) and native_limit > combined_limit:
        errors.append("native limit exceeds coordinator combined limit")
    same("combined enforcement", value(policy, "combined_limit_enforcement"), "coordinator")

    for name in NATIVE_ROLES:
        data = roles[name]
        same(f"{name}.name", data.get("name"), name)
        for setting in INHERITED_SETTINGS:
            if setting in data:
                errors.append(f"{name}.{setting}: custom agents inherit this session setting; remove this ineffective override")
        if name == "reviewer":
            model = value(canonical, "roles", "reviewer", "preferred_model")
            effort = value(canonical, "roles", "reviewer", "reasoning_effort")
        else:
            model = value(policy, "native_execution_model")
            effort = value(policy, "native_execution_effort")
        same(f"{name}.model", data.get("model"), model)
        same(f"{name}.model_reasoning_effort", data.get("model_reasoning_effort"), effort)
        for field in ("description", "developer_instructions"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                errors.append(f"{name}.{field}: expected nonempty text")

    task_path = root / ".ai/templates/task/task.yaml"
    if not task_path.exists():
        task_path = Path(__file__).resolve().parents[1] / "templates/task/task.yaml"
    try:
        task_data = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task = task_data if isinstance(task_data, dict) else {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"task template: {exc}")
        task = {}
    for role in ("planner", "reviewer"):
        same(f"new task {role}", value(task, "roles", role), value(canonical, "roles", role, "preferred_model"))
    return errors


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    errors = validate(Path.cwd())
    print(json.dumps({
        "status": "FAIL" if errors else "PASS",
        "scope": "offline repository agreement only; runtime routing, model access and permission enforcement NOT_RUN",
        "errors": errors,
    }, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
