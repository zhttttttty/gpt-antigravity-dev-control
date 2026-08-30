# Architecture Gate

Stop implementation if the task requires an unauthorized change to:

- database schema / migrations;
- public API or event contract;
- authentication / authorization;
- secrets, cryptography or trust boundary;
- core framework/runtime/storage engine;
- deployment topology;
- external service;
- persistent state or queue semantics;
- major dependency;
- backward compatibility contract;
- broad cross-module architecture.

Required artifact: accepted ADR or explicit task authorization.

Escalation token: `ARCHITECTURE_DECISION_REQUIRED`.
