# Observed route failure and bounded repair

Previous run2 background unittest task-42 completed69 tests in59.956s at15:26:10,
timer task-46 fired but agent passively narrated waiting. Subsequent partial code edits
occurred15:32+, so earlier tests do not validate them. Preserve old dirty worktree untouched.

Real diagnostic run_command python -B print123456 returned output in0.7s.
A second diagnostic command sleep2/print654321 returned TaskId; manage_task status on
that exact ID reported DONE and actual output. CLI wrapper tools are not interchangeable
with native CommandId. Never use schedule or merely say waiting in a single-print turn.

Windows grep_handler interpreted /UserData/... as line number when absolute D: path was
used. Search using relative paths and cwd, or terminal rg with relative paths; absolute
paths are still appropriate for native file editing. Do not force absolute search paths.

Repair only new task scope; save stream-json events if supported. Do not claim a tool
event exposes exit code when unavailable; unknown is UNKNOWN. Complete canonical receipt
requires actual immutable base from runtime run.json/context and committed final head.
The original controller scope hardcodes .agents protection; implement only a narrow
hash-approved exact self-repair exception, not writable-overrides-protected globally.
