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

    for c in commands:
        if "command" not in c:
            raise ValueError("Malformed command evidence: missing command field")
        if "status" in c:
            raise ValueError("Malformed command evidence: status field used instead of result")
        res = c.get("result")
        if res not in {"PASS", "FAIL", "NOT_RUN"}:
            raise ValueError(f"Malformed command result: {res!r}; expected PASS, FAIL, or NOT_RUN")
        if res == "PASS":
            if type(c.get("exit_code")) is not int or c.get("exit_code") != 0:
                raise ValueError("Command with result PASS must have integer exit_code 0")

    for e in evidence:
        if "id" in e and "acceptance_id" not in e:
            raise ValueError("Malformed acceptance evidence: id field used instead of acceptance_id")
        if "acceptance_id" not in e:
            raise ValueError("Malformed acceptance evidence: missing acceptance_id field")
        if "status" in e:
            raise ValueError("Malformed acceptance evidence: status field used instead of result")
        res = e.get("result")
        if res not in {"PASS", "FAIL", "NOT_RUN"}:
            raise ValueError(f"Malformed acceptance result: {res!r}; expected PASS, FAIL, or NOT_RUN")
        if not e.get("evidence"):
            raise ValueError("Malformed acceptance evidence: missing evidence content")

    required = [item["command"] for item in task["checks"].get("required", [])]
    passed = sum(any(c.get("command") == command and type(c.get("exit_code")) is int
                     and c["exit_code"] == 0 and c.get("result") == "PASS" for c in commands)
                 for command in required)
    ac_passed = sum(any(e.get("acceptance_id") == item["id"] and e.get("result") == "PASS"
                        and e.get("evidence") for e in evidence) for item in task["acceptance"])
    return passed, len(required), ac_passed, len(task["acceptance"])


def validate_unverified_items(task, unverified_items):
    """Only structured optional NOT_RUN items whose command matches task.checks.optional may remain unverified."""
    if not isinstance(unverified_items, list):
        return ["unverified_items must be a list"]
    if not unverified_items:
        return []
    optional_commands = [
        item["command"] if isinstance(item, dict) else item
        for item in task.get("checks", {}).get("optional", [])
    ]
    required_commands = [
        item["command"] if isinstance(item, dict) else item
        for item in task.get("checks", {}).get("required", [])
    ]
    errors = []
    for item in unverified_items:
        if not isinstance(item, dict):
            errors.append(f"Unstructured unverified item: {item!r}; must be mapping")
            continue
        cmd = item.get("command")
        if not cmd:
            errors.append("Unverified item missing command")
            continue
        if cmd in required_commands:
            errors.append(f"Required check {cmd!r} cannot be unverified")
            continue
        if cmd not in optional_commands:
            errors.append(f"Unverified item command {cmd!r} does not match any task.checks.optional command")
            continue
        if item.get("result") != "NOT_RUN":
            errors.append(f"Unverified item {cmd!r} result must be NOT_RUN; got {item.get('result')!r}")
            continue
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"Unverified item {cmd!r} requires nonempty reason")
            continue
    return errors


def validate_known_issues_done(executor, qa, review):
    known_issues = executor.get("known_issues") or []
    if not isinstance(known_issues, list):
        return ["Executor known_issues must be a list"]
    if not known_issues:
        return []

    errors = []
    if review.get("verdict") != "PASS_WITH_NOTES" or qa.get("verdict") != "PASS_WITH_NOTES":
        errors.append("Reported known issues require matching PASS_WITH_NOTES review and QA verdicts")

    exec_issue_texts = []
    for idx, item in enumerate(known_issues):
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            if "text" in item and "issue" not in item:
                errors.append(f"Executor known issue [{idx}] uses alias 'text'; field 'issue' required")
            if "description" in item and "issue" not in item:
                errors.append(f"Executor known issue [{idx}] uses alias 'description'; field 'issue' required")
            text = (item.get("issue") or "").strip()
        else:
            errors.append(f"Executor known issue [{idx}] malformed type: {type(item).__name__}")
            continue
        if not text:
            errors.append(f"Executor known issue [{idx}] has empty issue text")
        elif text in exec_issue_texts:
            errors.append(f"Duplicate executor known issue text: {text!r}")
        else:
            exec_issue_texts.append(text)

    if "issues_review" in qa:
        errors.append("QA issues_review alias is not permitted; use known_issues_review")

    qa_reviews = qa.get("known_issues_review")
    if not isinstance(qa_reviews, list):
        errors.append("QA known_issues_review must be a list when executor reports known issues")
        return errors

    if len(qa_reviews) != len(known_issues):
        errors.append(
            f"One-to-one independent QA disposition required: {len(known_issues)} issues reported, {len(qa_reviews)} reviewed"
        )

    reviewed_texts = []
    for i, item in enumerate(qa_reviews):
        if not isinstance(item, dict):
            errors.append(f"QA issue review [{i}] must be a mapping")
            continue
        if "text" in item and "issue" not in item:
            errors.append(f"QA issue review [{i}] uses alias 'text'; field 'issue' required")
        issue_text = (item.get("issue") or "").strip()
        if not issue_text:
            errors.append(f"QA issue review [{i}] missing issue text")
        elif issue_text in reviewed_texts:
            errors.append(f"Duplicate QA issue review for issue {issue_text!r}")
        elif issue_text not in exec_issue_texts:
            errors.append(f"QA issue review [{i}] references unrelated issue {issue_text!r}")
        else:
            reviewed_texts.append(issue_text)

        disposition = item.get("disposition")
        if disposition != "ACCEPTED_RESIDUAL":
            errors.append(f"QA issue review [{i}] disposition is {disposition!r}; only ACCEPTED_RESIDUAL allows DONE")
        evidence = item.get("evidence_checked")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"QA issue review [{i}] missing evidence_checked")

        approval = item.get("risk_owner_approval")
        if isinstance(approval, str):
            errors.append(
                f"QA issue review [{i}] plain string risk_owner_approval {approval!r} not permitted; "
                "structured mapping required with approved_by, result APPROVED, and evidence"
            )
        elif not isinstance(approval, dict):
            errors.append(f"QA issue review [{i}] missing risk-owner approval for accepted residual")
        else:
            approved_by = approval.get("approved_by")
            result = approval.get("result")
            app_evidence = approval.get("evidence")
            if not isinstance(approved_by, str) or not approved_by.strip():
                errors.append(f"QA issue review [{i}] structured risk_owner_approval requires nonempty approved_by identity")
            if result != "APPROVED":
                errors.append(f"QA issue review [{i}] structured risk_owner_approval result must be APPROVED; got {result!r}")
            if not isinstance(app_evidence, str) or not app_evidence.strip():
                errors.append(f"QA issue review [{i}] structured risk_owner_approval requires nonempty evidence")
            if approval.get("issue") and approval.get("issue") != issue_text:
                errors.append(f"QA issue review [{i}] structured risk_owner_approval issue mismatch: {approval.get('issue')!r} != {issue_text!r}")

    for text in exec_issue_texts:
        if text not in reviewed_texts:
            errors.append(f"Executor known issue {text!r} not reviewed in QA known_issues_review")

    return errors


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
    ws = executor.get("workspace")
    if not isinstance(ws, dict):
        errors.append("Executor workspace must be a mapping")
    else:
        for field in ("path", "branch", "base_commit", "head_commit"):
            val = ws.get(field)
            if not isinstance(val, str) or not val.strip():
                errors.append(f"Executor workspace.{field} must be a nonempty string")
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
    unverified_errs = validate_unverified_items(task, executor.get("unverified_items") or [])
    if unverified_errs:
        errors.extend(unverified_errs)
    issue_errs = validate_known_issues_done(executor, qa, review)
    if issue_errs:
        errors.extend(issue_errs)
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
    try:
        passed, required, accepted, total = evidence_counts(task, executor)
        if passed != required or accepted != total:
            errors.append("Required executor commands/acceptance evidence missing or failed")
    except ValueError as exc:
        errors.append(f"Invalid executor evidence: {exc}")
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
