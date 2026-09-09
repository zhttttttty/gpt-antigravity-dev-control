# Documentation Map

This project is organized around one local task-control workflow. The documents
below describe how to use it and how it works internally.

## Use the project

1. [Quick Start](QUICK_START.md) - install dependencies, create a task, route it,
   execute it, review evidence, and close it.
2. [Control Workflow](CONTROL_WORKFLOW.md) - the complete plan to execute to
   review to close lifecycle and the responsibilities of each role.
3. [Local Delegation Operations](LOCAL_DELEGATION.md) - agy probing, interactive
   approvals, full-access mode, recovery, receipts, diagnostics, and evidence.
4. [Execution Modes](EXECUTION_MODES.md) - when to use direct, delegated, or
   approval_required.

## Understand the implementation

1. [Architecture](ARCHITECTURE.md) - control-plane layers, authority boundaries,
   state ownership, and failure behavior.
2. [Current Limitations](LIMITATIONS.md) - capabilities that remain intentionally
   manual or local.
3. [Cost Measurement](../COST_METRICS.md) - how to compare direct and delegated
   tasks using observed data instead of assumed savings.
4. [Risk Gates](../.ai/rules/RISK_GATES.md) - required evidence and approval for
   low-, medium-, and high-risk changes.

## Repository conventions

- .ai/ contains contracts, state folders, templates, rules, and local runtime records.
- .ai/scripts/control.py is the primary command entry point.
- ai.py and delegate.py are compatibility modules behind that entry point.
- GEMINI.md describes the bounded executor role.
- CONTRIBUTING.md and SECURITY.md cover development and secret handling.
