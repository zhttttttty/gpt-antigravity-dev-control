# Cost metrics (measure, do not promise savings)

[中文](COST_METRICS.zh-CN.md)

Compare similarly scoped tasks completed directly by Codex and through local
delegation. Include both products' consumption, elapsed time, review effort,
rework and human intervention. Never equate CLI stdout bytes with billed tokens.

| Task / mode | Codex usage + source | Antigravity usage + source | Wall time | Reworks | Human interventions | Outcome |
|---|---|---|---|---|---|---|
| No measured production tasks yet | unknown | unknown | unknown | unknown | unknown | unmeasured |

Runtime compact receipts record controller elapsed seconds and nullable token
fields. Fill consumption from actual per-task/provider records when available.
Account-wide quota percentages cannot reliably be attributed to one task. Record
model/version, task scope and measurement window for comparisons. Include failed
attempts and review time. Subscription quota reduction, billed token reduction
and monetary savings are different measures. Phase one does not automatically
collect provider usage. No fixed percentage or total-cost reduction is guaranteed.
