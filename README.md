# Codex → Antigravity delegation

[中文说明](README.zh-CN.md)

Delegate a bounded change to agy in one command. The controller creates an isolated Git worktree,
saves logs, runs caller-supplied checks, and returns the actual changes for Codex to review.
Risk-adaptive task routing and deterministic verification remain available for complex or high-risk work.
The daily path is **doctor → run → runs**. The full protocol is reserved for complex tasks.

Version: **3.6.0-local**. The deliverable is `.agents/skills/antigravity-delegate/`.

## Everyday use

Use Git, Python 3.11+, and a working native agy installation. Copy the entire Skill into your
project's `.agents/skills/`, then review and commit the installation and intended baseline.
Alternatively, use an existing Skill's absolute script path with `--repo`; copying is optional.
The source checkout must have a commit and be clean; uncommitted and ignored files are not copied.

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
$ctl = Join-Path $PWD '.agents/skills/antigravity-delegate/scripts/control.py'
python $ctl doctor
python $ctl run "Document installation in README" --allow README.md --check "git diff --check"
python $ctl runs latest
```

`doctor` reads environment, Git and agy help information. Resolve its reported blockers; repeat
it only when troubleshooting. No init, model profile or task.yaml is required. Preview without calling agy:

```powershell
python $ctl run "Document installation in README" --allow README.md --dry-run
```

The command returns JSON with the worktree, diff, and check logs. Full results are retained under
`agy-runs/<run-id>/result.json` in the Git common metadata directory. Console lists show at most
20 paths. READY_FOR_REVIEW is a handoff, not acceptance; absent checks are marked NOT_RUN.
Use `runs` to list records, `runs RUN-ID` for a full result, or `runs latest` for the most recently
updated record. Review the diff, new files and check logs before explicitly integrating the changes.
Checks use native argv by default; opt into shell syntax with --shell-checks. Shared process execution
provides per-command and total timeouts and checks the workspace after each command.
The controller does not automatically commit, merge, retry, or discard the execution worktree.

## Advanced tasks

For architecture, security, migrations, deployment, persistent approvals, or repeated rework,
use the [full workflow](.agents/skills/antigravity-delegate/references/workflow.md).
The full path uses adaptive backend selection and prepare/launch/verify/collect. Existing schema v2
states, legacy required checks, approvals, receipts, and the DONE gate remain available.
For runs processed by verify, collection binds to the verified HEAD and receipt hash; older unsealed
verification needs fresh evidence. The legacy required-only direct collection path remains executor-reported.

## Boundaries

Writable scopes are checked after execution. A Git worktree is not an operating-system sandbox.
Native Codex agents inherit parent-session permissions; sandbox_mode in a custom agent file
cannot create a separate read-only boundary. Optional model profiles serve advanced orchestration;
offline configuration agreement does not prove runtime model access.
The implementation is tested with fake executors; actual agy access, task quality, and usage still
require measurement.

## Documentation

- [Everyday guide](.agents/skills/antigravity-delegate/references/quick-start.md), [CLI reference](.agents/skills/antigravity-delegate/references/cli.md).
- [Documentation map](docs/README.md), [workflow audit](docs/maintenance/workflow-audit-2026-11-01.md), [current status](docs/STATUS.md).
- [Contributing](CONTRIBUTING.md), [security](SECURITY.md), [cost measurement](COST_METRICS.md).

Historical material and independent nested checkouts are preserved; consult the folder guide.
License: [MIT](LICENSE).
