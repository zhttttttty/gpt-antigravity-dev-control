# ADR-001: Local delegation as the preferred V3.1 path

Status: accepted for implementation by the project owner's V3.1 request.

Keep the V2 contract, state machine, receipts and merge gates. Add a separate
Python CLI using local Git worktrees and a replaceable executor adapter. Leave
the V3 Lite remote orchestrator unchanged and explicitly experimental.

The planner selects direct, delegated or approval-required execution. Every
local launch requires confirmation. CLI discovery does not prove login or
headless execution; command arguments must be checked against installed help
(the default print-mode shape was verified against agy 1.0.10). Launch success
is not implementation completion. Collection emits
compact evidence for independent review, never auto-merges or calls a reviewer
API. Full logs remain local. Worktrees are isolation, not a security sandbox.

Phase one excludes unattended loops, automatic retry, dependency scheduling,
automatic test execution by the controller and token-savings guarantees.
