# TalkToBot engineering quality scorecard

Current release score: **Not assessed**. A numerical score without executed checks would be misleading.

| Domain | Weight | Evidence required |
|---|---:|---|
| Security and tenant isolation | 20% | threat model, SAST/DAST, cross-tenant tests |
| Correctness | 20% | acceptance and regression tests |
| Architecture and maintainability | 15% | reviewed dependency and design boundaries |
| Testing and CI/CD | 15% | CI logs and coverage reports |
| Reliability and recovery | 10% | failure injection, backup restore and rollback |
| Performance and scalability | 10% | load tests and measured p95 latency |
| Observability and operations | 5% | traces, metrics and alert verification |
| Documentation and accessibility | 5% | runbooks and accessibility tests |

Mandatory release blockers override weighted average. 9.5+/10 target is not a production guarantee.
