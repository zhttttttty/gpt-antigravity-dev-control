# Bootstrap Prompts

## GPT-5.6 Sol — Initialize Project

```text
Read AGENTS.md, .ai/config.yaml and all files under .ai/project/, .ai/rules/ and .ai/state/.
Act as PM + system architect.
Initialize PROJECT.md, REQUIREMENTS.md, ARCHITECTURE.md, ROADMAP.md, ACCEPTANCE.md and PROJECT_STATE.yaml from the user's project brief and existing repository.
Do not implement application code yet.
Identify architecture invariants, protected areas, key risks and the first independently reviewable task.
Create the task from .ai/templates/task/ under .ai/tasks/queue/ and validate that its risk, authority, scope and acceptance evidence are explicit.
```

## GPT-5.6 Sol — Create Next Task

```text
Read canonical .ai/ artifacts and current Git/project state.
Create the next smallest independently reviewable READY task.
Use structured task.yaml.
Set risk based on impact, not confidence.
Set explicit writable/protected scope, authority flags, isolation, acceptance criteria and required checks.
Do not write implementation code.
```

## Antigravity — Execute Assigned Task

```text
Read GEMINI.md, AGENTS.md, .ai/config.yaml, relevant project/architecture files, PROJECT_STATE.yaml and the assigned task folder.
Execute exactly this task in its designated worktree.
Do not change task scope or architecture authority.
Run required checks and fill receipt.executor.yaml with actual evidence.
If an architecture/scope gate is hit, stop and report the appropriate escalation token.
Do not self-approve or merge.
```

## GPT-5.6 Sol — Review

```text
Act as independent reviewer and acceptance owner.
Read the task contract, exact Git diff/commit range, executor receipt, test evidence, relevant architecture/ADRs and risk gate.
Fill receipt.qa.yaml and review.yaml.
Return PASS, PASS_WITH_NOTES, REWORK or BLOCKED.
Do not silently edit the implementation while reviewing.
If REWORK is required, produce bounded findings and transition the task back to READY or create a separate fix task.
```
