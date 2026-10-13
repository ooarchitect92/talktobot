# Deployment runbook — draft

Status: not validated in any environment.

1. Pin release commit and collect signed build artefacts, dependency manifest and test evidence.
2. Validate secrets and infrastructure/environment isolation; forbid production secrets in CI logs.
3. Back up production state and verify restore checkpoint and migration compatibility.
4. Deploy backward-compatible migrations to staging; run smoke and authorization tests.
5. Promote an approved artefact via controlled canary/blue-green deploy.
6. Monitor error rates, p95 API latency, payment reconciliation, queue depth and tenant access anomalies.
7. Stop rollout and revert service release on failed gates. Database rollback must use an explicitly rehearsed migration/forward-fix strategy.
8. Record release approver, artifact digest, migration version, monitoring links and rollback result.

Actual environment endpoints, deployment credentials and operational commands must be confirmed before using this as an executable production runbook.
