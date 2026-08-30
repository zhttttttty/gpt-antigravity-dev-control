# Review Workflow

1. Read task contract as written for the current contract revision.
2. Confirm exact implementation diff/commit range.
3. Confirm executor receipt corresponds to that workspace/revision.
4. Check scope and protected paths.
5. Check each acceptance criterion against evidence and code.
6. Check required risk gates.
7. Check regression/security/maintainability.
8. Record findings in QA receipt and review.yaml.
9. Return PASS / PASS_WITH_NOTES / REWORK / BLOCKED.
10. Do not silently fix implementation while acting as reviewer.
