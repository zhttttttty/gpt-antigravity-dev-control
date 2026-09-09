# Contributing

Contributions are welcome.

## Principles

- Keep Core Protocol semantics backward-compatible unless a versioned migration is provided.
- Keep the executor bounded by `task.yaml` authority.
- Prefer repository evidence over model claims.
- Keep the control plane local-first and summary-first; do not add remote scheduling or reviewer
  services to `main`.

## Development

```bash
python -m pip install -r .ai/scripts/requirements-local.txt
python -m compileall .ai/scripts .ai/adapters .agents/skills
python .ai/scripts/control.py status
python .ai/scripts/control.py --help
python -m unittest discover -s tests -v
```

Before changing task schema, Risk Gates, Receipt formats or state transitions, update documentation and `CHANGELOG.md`.

Use pull requests for non-trivial changes. Include what changed, why, compatibility impact and how it was tested.
