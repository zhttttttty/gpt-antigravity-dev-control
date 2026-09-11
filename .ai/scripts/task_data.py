"""Shared structured task data and evidence validation; no provider calls."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"YAML keys must be unique strings: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse_yaml(text):
    if len(text.encode("utf-8")) > 128_000:
        raise ValueError("YAML exceeds 128KB")
    try:
        data = yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Expected YAML mapping")
    return data


def read_yaml(path):
    if path.stat().st_size > 128_000:
        raise ValueError(f"YAML exceeds 128KB: {path}")
    return parse_yaml(path.read_text(encoding="utf-8"))


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def task_id(value):
    if not re.fullmatch(r"TASK-[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("Task ID must be TASK- followed by letters, digits, _ or -")
    return value


def digest(task):
    data = {key: value for key, value in task.items() if key not in {"status", "metadata"}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def require_approval(task, ident, path):
    data = read_yaml(Path(path)) if path else {}
    if not (data.get("task_id") == ident and data.get("contract_sha256") == digest(task)
            and data.get("result") == "APPROVED" and data.get("approved_by") and data.get("evidence")):
        raise ValueError(f"Pre-review approval required for contract {digest(task)}; see docs/LOCAL_DELEGATION.md")
    return data


def evidence_counts(task, receipt):
    commands = receipt.get("commands") or []
    evidence = receipt.get("acceptance_evidence") or []
    if not isinstance(commands, list) or not all(isinstance(c, dict) for c in commands):
        raise ValueError("Invalid commands evidence")
    if not isinstance(evidence, list) or not all(isinstance(c, dict) for c in evidence):
        raise ValueError("Invalid acceptance evidence")
    required = [item["command"] for item in task["checks"].get("required", [])]
    passed = sum(any(c.get("command") == command and type(c.get("exit_code")) is int
                     and c["exit_code"] == 0 and c.get("result") == "PASS" for c in commands)
                 for command in required)
    ac_passed = sum(any(e.get("acceptance_id") == item["id"] and e.get("result") == "PASS"
                        and e.get("evidence") for e in evidence) for item in task["acceptance"])
    return passed, len(required), ac_passed, len(task["acceptance"])


def done_errors(task, folder):
    executor = read_yaml(folder / "receipt.executor.yaml")
    qa = read_yaml(folder / "receipt.qa.yaml")
    review = read_yaml(folder / "review.yaml")
    errors = []
    for label, receipt in (("executor", executor), ("qa", qa), ("review", review)):
        expected = {"schema_version": 2, "task_id": task["id"], "attempt": task["attempt"]}
        if label != "review":
            expected["contract_revision"] = task["contract_revision"]
        for key, value in expected.items():
            if type(receipt.get(key)) is not type(value) or receipt.get(key) != value:
                errors.append(f"{label} identity/revision mismatch: {key}")
    if executor.get("status") != "COMPLETE" or not executor.get("executor"):
        errors.append("Executor must be COMPLETE with an actual identity")
    if qa.get("status") != "REVIEWED" or not qa.get("reviewer") or not qa.get("reviewed_at"):
        errors.append("QA must be REVIEWED with reviewer and reviewed_at")
    if qa.get("reviewer") == executor.get("executor"):
        errors.append("QA reviewer must be independent of executor")
    verdict = review.get("verdict")
    if verdict not in {"PASS", "PASS_WITH_NOTES"} or qa.get("verdict") != verdict:
        errors.append("Matching QA/review PASS or PASS_WITH_NOTES verdicts required")
    if not review.get("summary"):
        errors.append("Review summary required")
    if qa.get("blocking_findings") != []:
        errors.append("QA blocking_findings must be an empty list")
    if executor.get("unverified_items") != []:
        errors.append("Executor unverified_items must be empty")
    architecture = executor.get("architecture_deviation")
    if not isinstance(architecture, dict) or architecture.get("result") != "NONE":
        errors.append("Architecture deviation requires a revised contract and fresh evidence")
    for section in ("risk_gate", "scope_review"):
        item = qa.get(section)
        if not isinstance(item, dict) or item.get("result") != "PASS":
            errors.append(f"QA {section}.result must be PASS")
    gate = qa.get("risk_gate") or {}
    if isinstance(gate, dict) and (gate.get("tier") != task["planning"]["risk"] or gate.get("missing_evidence") != []):
        errors.append("QA risk tier must match and missing_evidence must be empty")
    scope = executor.get("scope_check")
    if not isinstance(scope, dict) or scope.get("result") != "PASS" or scope.get("out_of_scope_files") != []:
        errors.append("Executor scope check must PASS without out-of-scope files")
    passed, required, accepted, total = evidence_counts(task, executor)
    if passed != required or accepted != total:
        errors.append("Required executor commands/acceptance evidence missing or failed")
    acceptance = qa.get("acceptance_review")
    if not isinstance(acceptance, list) or not all(isinstance(item, dict) for item in acceptance):
        errors.append("QA acceptance_review must be a list of mappings")
    elif any(not any(item.get("acceptance_id") == ac["id"] and item.get("result") == "PASS"
                     and item.get("evidence_checked") for item in acceptance) for ac in task["acceptance"]):
        errors.append("Independent QA evidence required for every acceptance criterion")
    architecture_review = qa.get("architecture_review")
    if not isinstance(architecture_review, dict) or architecture_review.get("result") not in ("PASS", "NOT_APPLICABLE"):
        errors.append("QA architecture review must PASS or be NOT_APPLICABLE")
    if task["planning"]["risk"] in ("medium", "high"):
        regression = qa.get("regression_review")
        if not isinstance(regression, dict) or regression.get("result") != "PASS":
            errors.append("Medium/high risk requires regression_review PASS")
    controls = task["risk_controls"]
    if controls.get("cross_family_review_required"):
        cross = qa.get("cross_family_review")
        if not isinstance(cross, dict) or cross.get("result") not in ("PASS", "WAIVED") or not cross.get("reviewer"):
            errors.append("Cross-family review needs PASS/WAIVED and reviewer identity")
        elif cross["result"] == "WAIVED" and not cross.get("findings"):
            errors.append("Cross-family waiver requires documented human waiver in findings")
    if controls.get("human_merge_approval_required"):
        human = qa.get("human_approval")
        if not isinstance(human, dict) or human.get("result") != "APPROVED" or not human.get("approved_by") or not human.get("approved_at"):
            errors.append("Human merge approval needs APPROVED, approved_by and approved_at")
    if controls.get("rollback_plan_required") and not (folder / "rollback.md").read_text(encoding="utf-8").strip():
        errors.append("Non-empty rollback plan required")
    return errors
