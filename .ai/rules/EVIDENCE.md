# Evidence Standard

A task is accepted on evidence, not confidence.

## Executor Evidence

- exact changed files;
- base/head commit when available;
- command + exit code;
- test/check result;
- acceptance criterion mapping;
- known issues;
- unverified items;
- architecture deviation statement.

## Reviewer Evidence

- scope verdict;
- risk gate verdict;
- acceptance verdict for each AC;
- regression/security findings;
- exact blocking findings;
- final verdict.

Use explicit states: `PASS`, `FAIL`, `NOT_RUN`, `UNKNOWN`, `NOT_APPLICABLE`.
