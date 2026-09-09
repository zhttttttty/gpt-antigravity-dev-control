# Execution modes and capability mapping

`direct`, `delegated`, and `approval_required` are controller routes in the task contract. They are not values for `agy --mode`.

Before every run, probe the executable with `--version`, `--help`, `agent`, `agents`, and `agent list`. Treat the help output as the source of truth for supported flags and mode values. The current known `agy` values are `accept-edits` and `plan`, but adapters must not hard-code that assumption.

| User intent | agy mapping | Required constraint |
| --- | --- | --- |
| Full access to the disposable worktree | Omit `--sandbox` | This does not expand the task contract or authorization scope. |
| Automatically approve tool calls | Add `--dangerously-skip-permissions` only when advertised by `--help` | Use only after explicit approval and only in an isolated worktree. |
| Read-only review | `--mode plan` | Prompt must forbid create, edit, delete, commit, merge, and push. |
| Normal implementation | `--mode accept-edits` when supported | Keep the task scope, receipt, test, and review gates. |

If a requested flag is not advertised, fail closed and report the unsupported capability. Never translate the controller route `direct` into an invented agy mode. The launch wrapper must pass arguments as an array (or `ProcessStartInfo.ArgumentList`) rather than concatenate a shell command.
