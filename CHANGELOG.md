# Changelog

All notable changes are documented here.

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
