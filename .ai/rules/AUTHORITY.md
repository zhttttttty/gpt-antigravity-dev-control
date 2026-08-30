# Authority Matrix

| Decision | GPT-5.6 Architect/Planner | Antigravity Executor | GPT-5.6 Reviewer | Human |
|---|---:|---:|---:|---:|
| Clarify requirement | yes | flag ambiguity | yes | final |
| Create task scope | yes | no | may request revision | final |
| Implement within scope | optional | yes | no | yes |
| Change architecture | yes | no | may reject/request ADR | final |
| Change schema/API/auth | only with explicit decision | no by default | review | final |
| Run tests | may | yes | may independently verify | yes |
| Self-approve implementation | no | no | yes as reviewer | final |
| Lower risk | planner/reviewer only with evidence | no | yes with justification | final |
| Merge high-risk change | no automatic authority | no | recommendation | explicit approval |
