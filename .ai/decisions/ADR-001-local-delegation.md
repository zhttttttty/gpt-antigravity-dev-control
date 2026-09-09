# ADR-001: Local delegation inside the unified control plane

[中文](ADR-001-local-delegation.zh-CN.md)

Status: accepted and unified with the Core Protocol.

Keep the task contract, state machine, receipts and merge gates. Add local Git
worktree delegation through a replaceable executor adapter. Expose task and
delegation operations through one `control.py` entry point while retaining the
older Python files as compatibility modules. The
former V3 Lite remote implementation is preserved on `archive/v3-lite` and
removed from `main` because this project does not require remote concurrent
scheduling.

The planner selects direct, delegated or approval-required execution. Every
local launch requires confirmation. CLI discovery does not prove login or
headless execution; command arguments must be checked against installed help
(the default print-mode shape was verified against agy 1.0.10). Launch success
is not implementation completion. Collection emits
compact evidence for independent review, never auto-merges or calls a reviewer
API. Full logs remain local. Worktrees are isolation, not a security sandbox.

Phase one excludes unattended loops, automatic retry, dependency scheduling,
automatic test execution by the controller and token-savings guarantees.
