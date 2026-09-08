# V3.1 Local Delegation

**Codex plans and reviews; Antigravity implements; a human approves merge.**
No remote reviewer API, automatic merge, background scheduler or automatic retry
is required. V2 is unchanged; V3 Lite remains an optional experimental provider
path in `.ai/orchestrator/`.

## Setup

Python 3.10+ and Git are required:

```sh
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/delegate.py --help
python .ai/scripts/delegate.py probe
```

On Windows, agy may be installed without a PATH entry:

```powershell
python .ai/scripts/delegate.py probe --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
```

The adapter probes `--version` and `help`, storing output locally. The shipped
print-mode argument shape was verified with agy **1.0.10** help, not assumed from
the Antigravity desktop executable. Default execution uses `--print-timeout 20m`
and `-p <prompt>` from the isolated worktree. It does not parse stdout as JSON:
agy prints text, and the executor must write the structured receipt file.
The model remains the CLI's configured default. No Hermes installation is needed.

Help/version success does **not** prove authentication or tool permissions.
Authenticate interactively when prompted. The controller does not add
`--dangerously-skip-permissions`. A noninteractive permission prompt may require
manual intervention; never interpret it as success. For version-specific
arguments, `launch --args-file local-argv.json` takes a JSON string array with
`{worktree}`, `{context}`, `{receipt}` placeholders (literal braces need doubling).
Arguments are passed without a shell. Windows batch wrappers are rejected; use
a native executable. Set an outer command timeout of at least 1260 seconds.

## Codex skill

The checked-in `.agents/skills/antigravity-delegate/SKILL.md` is repo-discoverable.
Invoke `$antigravity-delegate` from this checkout. No global configuration changes
are made. For another project, copy the skill and `.ai` control-plane files as
appropriate, preserving existing project requirements. Follow the current
[official skill documentation](https://learn.chatgpt.com/docs/build-skills) when
installing in a different scope; do not assume a permanent global install path.

## One-task workflow

1. Copy `.ai/templates/task` into `.ai/tasks/queue/TASK-001`, replace placeholders,
   preserve list indentation, set a bounded writable scope and real acceptance
   criteria/test commands. Add the execution block below. Commit the task.
2. Use a clean checkout. `isolation.base_branch` must resolve to the current HEAD
   containing the task; no missing-base fallback is permitted. Set it to your
   actual planning branch or `HEAD`. Worktree isolation is mandatory here.
3. Inspect routing, confirm execution, prepare and launch:

```sh
python .ai/scripts/ai.py validate TASK-001
python .ai/scripts/delegate.py route TASK-001
python .ai/scripts/delegate.py prepare TASK-001 --approve
python .ai/scripts/delegate.py launch TASK-001 --approve --executable /absolute/path/to/agy
python .ai/scripts/delegate.py status TASK-001
python .ai/scripts/delegate.py collect TASK-001
```

```yaml
execution:
  mode: delegated
  adapter: antigravity_cli
  model: configured_default
  context_budget: compact
  report_level: summary
  max_execution_attempts: 2
  escalation: codex_review
```

`direct` is the default for old tasks without this block. Small fixes/config/docs
usually stay direct. Independent multi-file implementation/test tasks are good
delegation candidates. `approval_required`, high risk, or enabled architecture
authority requires a pre-review approval file in addition to --approve:

```yaml
task_id: TASK-001
contract_sha256: <hash from route>
result: APPROVED
approved_by: <human name>
evidence: <ADR or explicit review reference>
```

Store it under ignored `.ai/runtime/` and pass `--approval-file <path>` to prepare.
This is an audit record bound to the contract, not identity authentication and
not permission for merge. Existing high-risk QA, cross-family and human merge
gates still apply. Task dependencies must already be DONE/ARCHIVED; there is no
dependency scheduler.

## Evidence and review

Prepare creates `.worktrees/TASK-001-1` on `ai/local/TASK-001-1`, records the base
SHA and contract digest, and moves the controller checkout's task to IN_PROGRESS.
The execution branch retains the original committed task snapshot. Only the
controller checkout owns state transitions; do not run another queue worker on
the worktree. Do not run local and remote controllers on the same task.

The context pack has a hard **32KB UTF-8 limit**, not an estimated token limit.
It contains the task, brief, context and rollback; code/rules are read on demand.
Oversized context is rejected, never silently truncated. Full logs and diffs
stay in `.ai/runtime/logs/TASK-001/run-N/` and are ignored by Git. Keep runtime
evidence backed up locally if you need durable recovery; no secrets belong in
context packs or committed receipts.

The executor writes `.ai/runtime/delegation/receipt.executor.yaml` in its
worktree and commits only implementation files. `collect` checks Git ancestry,
branch, dirty/untracked files, receipt identity and reported required checks/ACs.
Scope checks cover additions, modifications, deletions and both sides of renames.
Control files are always protected. Worktrees are **not a security sandbox**;
scope is a post-execution review gate, not OS-level enforcement.

Compact JSON includes SHAs, file count/preview, scope result, reported command
and acceptance counts, pending review, elapsed time and local evidence paths.
It does not manufacture individual test counts, token totals or independent PASS.
Missing evidence remains blocked. Actual test logs should be referenced by the
executor; collection preserves but does not independently rerun those commands.

Codex reviews selected diffs/tests, writes V2 QA/review artifacts, and invokes
V2 transitions. COMPLETE leads only to REVIEW. Human integration stays explicit:
commit controller artifacts, review/merge the implementation branch, reconcile
PROJECT_STATE.yaml and preserve the task state. The controller never calls a
model to review, never merges and never declares DONE.

## Failures and recovery

- No executable/login: fix the environment; no fake success. Probe exit 2 means
  discovery failed. Probe does not make a model call.
- Launcher timeout/nonzero: inspect launch.log. The direct process is terminated
  on timeout, but descendants/remote work may continue. Do not blindly relaunch.
- Launch is one-shot for a prepared run; manual completion may still be collected
  after a failed launch. PREPARED can also be completed through the interactive
  CLI using the generated context without invoking launch.
- Missing/dirty receipt: fix the executor artifacts and collect again. Scope or
  failed reported checks move the task to BLOCKED, preserving full evidence.
- REWORK: V2 REVIEW → READY archives receipts/increments attempt. BLOCKED → READY
  is manual recovery. Commit controller state before preparing the next attempt.
- Each preparation consumes one budget slot, including interrupted setup. At the
  limit escalate to Codex/human; never delete history to conceal failures.
- Interrupted PREPARING/LAUNCHING or stale delegation.lock: inspect run.json, Git
  worktrees/branches and processes. Retain user changes and evidence, then perform
  explicit manual recovery. Crash-safe multi-file transactions are not provided.
- Runtime cleanup, parallel runs, automatic retries, metrics ingestion and batch
  scheduling are deferred. No automatic worktree removal is performed.

## Local validation

```sh
python -m unittest discover -s tests -v
python -m compileall .ai/scripts .ai/adapters .agents/skills
```

Tests use temporary Git repositories and a native Python subprocess fixture;
they do not spend Antigravity quota or demonstrate Gemini coding quality.

Implementation-time checks on Windows: agy 1.0.10 version/help succeeded.
A minimal `-p` connection prompt with a 30-second print timeout exited 0 but
returned no captured text. This is **inconclusive**, not a verified login or
end-to-end model task. Resolve this locally before trusting real delegation.
