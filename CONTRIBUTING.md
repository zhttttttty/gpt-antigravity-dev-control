# Contributing

Contributions are welcome.

## Principles

- Keep V2 protocol semantics backward-compatible unless a versioned migration is provided.
- Keep the executor bounded by `task.yaml` authority.
- Prefer repository evidence over model claims.
- Keep V3 Lite lightweight; avoid infrastructure dependencies without a clear need.

## Development

```bash
python -m pip install -r .ai/orchestrator/requirements.txt
python -m compileall .ai/scripts .ai/orchestrator
python .ai/scripts/ai.py status
python .ai/orchestrator/orchestrator.py --help
```

Before changing task schema, Risk Gates, Receipt formats or state transitions, update documentation and `CHANGELOG.md`.

Use pull requests for non-trivial changes. Include what changed, why, compatibility impact and how it was tested.
