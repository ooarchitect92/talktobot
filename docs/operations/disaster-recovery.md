# Disaster recovery plan — draft

Status: objectives proposed, no restoration drill completed.

- Proposed initial RPO <= 15 minutes and RTO <= 60 minutes, subject to infrastructure and customer contract review.
- Encrypt backups, minimize cross-account permissions and verify retention and deletion compliance.
- Restore PostgreSQL to an isolated recovery environment; verify records, access boundaries, schema version and application correctness.
- Recover file/object storage with consistent tenant ownership and encryption controls.
- Reconcile payment-provider state after restore before retrying billing webhooks.
- Rebuild background-job queues with idempotency to avoid duplicate side effects.
- Reissue or revoke compromised API credentials and restore secrets from managed vault.
- Exercise incident communication, monitoring and failover procedures at defined intervals.

Attach drill timestamps, restore logs, integrity checks and signed approval before claiming recovery targets are met.
