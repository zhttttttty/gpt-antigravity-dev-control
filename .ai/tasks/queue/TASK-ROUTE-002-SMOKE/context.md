# Bounded smoke context

Do not inspect history, old tasks, other source, accounts, network, or spawn agents.
The target is a NEW file; implement immediately with native file editing.
Use worktree cwd for commands. TaskId -> manage_task status; CommandId -> command_status.
Never schedule a timer or passively narrate waiting. Budget180 seconds total.

Required commands after final edit:
python -B -m unittest discover -s tests -p test_route_smoke.py -v
git diff --check ai/route-smoke-baseline...HEAD

The adapter supplies the exact runtime receipt path and precreated template.
Read git rev-parse HEAD before committing for immutable base_commit, then read
HEAD after commit for head_commit. No governance/QA/review edits or merge.
Keep schema fields: status COMPLETE; executor antigravity; task_id TASK-ROUTE-002-SMOKE;
contract_revision1; attempt1; workspace path/branch/base_commit/head_commit all nonempty.
commands: command exact string, exit_code0, result PASS, actual evidence.
acceptance_evidence: acceptance_id AC-S001 through AC-S004, result PASS and evidence.
AC-S004 executor evidence must say collection and independent review are pending;
you cannot self-approve that AC. Root verifies this post-execution condition.
changed_files only tests/test_route_smoke.py; scope_check PASS; architecture_deviation NONE;
known_issues/unverified_items empty only if genuinely no issues. Use actual timestamps.
Fill canonical runtime receipt through native file editing after implementation commit, then STOP.
