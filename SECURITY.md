# Security Policy

## Reporting

Do not publish API keys, GitHub PATs, private repository credentials or other secrets in issues, task receipts or logs.

For a suspected vulnerability, open a minimal GitHub issue without sensitive exploit data and request a private follow-up channel from the repository owner.

## Secret handling

V3 Lite expects secrets through environment variables such as:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `ANTIGRAVITY_GITHUB_PAT`

Never commit these values. Runtime SQLite files and `.env*` are ignored by default.

## High-risk changes

Authentication, authorization, destructive data behavior, database migrations, deployment topology and breaking public contracts should be classified as high risk and must pass the repository's high-risk gate before merge.
