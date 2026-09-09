# Security Policy

[中文](SECURITY.zh-CN.md)

## Reporting

Do not publish API keys, GitHub PATs, private repository credentials or other secrets in issues, task receipts or logs.

For a suspected vulnerability, open a minimal GitHub issue without sensitive exploit data and request a private follow-up channel from the repository owner.

## Secret handling

The local control plane delegates through the user's agy installation. Keep authentication in
the CLI's supported credential store; do not copy tokens, account data, or private
repository credentials into task contracts, context packs, receipts, or commits.

`.env*`, `.ai/runtime/`, and local execution logs are ignored by default. Logs may
still contain source snippets, paths, prompts, or provider diagnostics; sanitize
them before attaching them to an issue.

## Full-access execution

`--full-access` is an explicit launch option for a disposable trusted worktree.
It forwards agy's permission-bypass flag but does not grant administrator rights
or create an OS sandbox. Review the task scope and worktree contents before use.

## High-risk changes

Authentication, authorization, destructive data behavior, database migrations, deployment topology and breaking public contracts should be classified as high risk and must pass the repository's high-risk gate before merge.
