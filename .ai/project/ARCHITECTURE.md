# Architecture

## Architecture Summary
`<one-paragraph system description>`

## System Context
`<actors, external systems, boundaries>`

## Components
| Component | Responsibility | Interface | Persistent State |
|---|---|---|---|
| `<name>` | `<role>` | `<API/event/file>` | `<yes/no + where>` |

## Data Flow
`<main request/event/data flow>`

## Public Contracts
- `<API / CLI / file schema / event>`

## Data Model / Persistence
- `<storage and schema principles>`

## Security Boundaries
- `<auth, secrets, trust boundaries>`

## Deployment / Runtime
- `<runtime topology>`

## Error Handling / Recovery
- `<failure behavior>`

## Observability
- `<logs, metrics, traces>`

## Performance / Scaling Assumptions
- `<assumptions>`

## Architecture Invariants
These cannot change without an accepted ADR / explicit architecture approval.

- `ARCH-INV-001: <invariant>`

## Protected Areas
- `<path or subsystem>`

## Architecture Gate
Changes affecting schema, public contracts, security, core frameworks, deployment, external services or persistent-state semantics require an ADR before implementation.
