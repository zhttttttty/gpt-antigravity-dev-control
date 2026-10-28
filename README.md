# Codex → Antigravity delegation

[中文说明](README.zh-CN.md)

Delegate a bounded change to agy in one command. The controller creates an isolated Git worktree,
saves logs, runs caller-supplied checks, and returns the actual changes for Codex to review.
Risk-adaptive task routing and deterministic verification remain available for complex or high-risk work.
This version integrates GitHub main at db1426b while retaining the local daily entry point and installation fixes.

Version: **3.5.0-local**. The deliverable is `.agents/skills/antigravity-delegate/`.

## Everyday use

Use Git, Python 3.11+, and a working agy installation. Copy the entire Skill into your project.
The source checkout must have a commit and be clean; uncommitted and ignored files are not copied.

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
python .agents/skills/antigravity-delegate/scripts/control.py run "Document installation in README" --allow README.md --check "git diff --check"
```

No init, model profile, task.yaml, or manual receipts are required. Preview without calling agy:

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "Document installation in README" --allow README.md --dry-run
```

The command returns JSON with the worktree, diff, and check logs. Full results are retained under
`agy-runs/<run-id>/result.json` in the Git common metadata directory. Console lists show at most
20 paths. READY_FOR_REVIEW is a handoff, not acceptance; absent checks are marked NOT_RUN.
Checks use native argv by default; opt into shell syntax with --shell-checks. Shared process execution
provides per-command and total timeouts and checks the workspace after each command.
The controller does not automatically commit, merge, retry, or discard the execution worktree.

## Advanced tasks

For architecture, security, migrations, deployment, persistent approvals, or repeated rework,
use the [full workflow](.agents/skills/antigravity-delegate/references/workflow.md).
The full path uses adaptive backend selection and prepare/launch/verify/collect. Existing schema v2
states, legacy required checks, approvals, receipts, and the DONE gate remain compatible.

## Boundaries

Writable scopes are checked after execution. A Git worktree is not an operating-system sandbox.
Native Codex agents inherit parent-session permissions; sandbox_mode in a custom agent file
cannot create a separate read-only boundary. Optional model profiles serve advanced orchestration;
offline configuration agreement does not prove runtime model access.
The implementation is tested with fake executors; actual agy access, task quality, and usage still
require measurement.

## Documentation

- [Everyday guide](.agents/skills/antigravity-delegate/references/quick-start.md), [CLI reference](.agents/skills/antigravity-delegate/references/cli.md).
- [Documentation map](docs/README.md), [integration record](docs/maintenance/upstream-integration-2026-10-28.md), [current status](docs/STATUS.md).
- [Contributing](CONTRIBUTING.md), [security](SECURITY.md), [cost measurement](COST_METRICS.md).

Historical material and independent nested checkouts are preserved; consult the folder guide.
License: [MIT](LICENSE).
