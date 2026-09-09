# Changelog

All notable changes are documented here.

## [3.1.2-local] - 2026-09-09

- Unify direct, delegated, and approval-required work under one Core Protocol.
- Add `.ai/scripts/control.py` as the primary CLI while retaining `ai.py` and
  `delegate.py` as compatibility modules.
- Remove the duplicate `.ai/VERSION`; root `VERSION` is now authoritative.
- Replace V2/V3.1 mode comparisons with execution-mode and unified-workflow docs.
- Limit main-branch CI to the unified CLI and add facade routing tests.

## [3.1.1-local] - 2026-09-09

- Preserve the former V3 Lite implementation on `archive/v3-lite` and remove its
  remote API adapters, SQLite coordination layer, CLI, configuration, and CI
  hooks from `main`.
- Make V3.1 local delegation the sole primary path on `main`; keep V2-compatible
  manual commands and all task/risk/receipt/worktree protocol guarantees.
- Update documentation, security guidance, contribution checks, and issue/PR
  templates for the local-only architecture.

## [3.1.0-local] - 2026-09-09

- Add terminal-inheriting interactive launch and one confirmed recovery with
  separate logs; reject redirected interactive sessions before changing state.
- Detect permission-denied/no-receipt exits as NEEDS_ATTENTION, expose sanitized
  diagnostic categories, and strengthen worktree-only executor prompts.
- Document the assisted real-task validation and its unresolved unattended limits.
- Add explicit opt-in `--full-access --approve` forwarding for trusted disposable
  worktrees; default interactive permissions remain unchanged.

- Add local routing, confirmed worktree preparation, agy print-mode adapter,
  compact receipt collection and preserved local evidence.
- Add repo-scoped Codex delegation skill and measured-cost guidance.
- Preserve V2 state/review gates; the V3 Lite remote code was still present in
  this release and is now retained in Git history and `archive/v3-lite`.
- Add offline Git/process integration tests; no automatic merge or retry loop.

## [3.0.0-lite] - 2026-08-30

### Added
- SQLite runtime coordination.
- Lease/heartbeat-oriented orchestration state.
- Antigravity executor provider adapter.
- GPT-5.6 Sol reviewer provider adapter.
- Automated READY → execution → review loop.
- Human approval gate for high-risk tasks.

### Preserved
- V2 task contracts, receipts, risk gates, ADRs, state folders and worktree isolation remain canonical protocol artifacts.

## [2.0.0] - 2026-08-30

### Added
- Structured `task.yaml` contracts.
- Folder-backed task state machine.
- Low/medium/high Risk Gates.
- Executor and QA Receipts.
- `GEMINI.md` executor adapter.
- Git Worktree isolation.
- Architecture authority gate.
- Attempt history for REWORK.
- Pure-Python `.ai/scripts/ai.py` helper.
