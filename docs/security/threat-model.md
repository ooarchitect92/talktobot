# Preliminary SaaS threat model

Status: initial design model; full application threat assessment pending.

## Assets
Customer identity, API tokens, subscription/price contracts, billing provider credentials, tenant data, AI conversation/document data, privileged audit trails and deployment secrets.

## Trust boundaries
Browser -> API; API -> database/cache/object store; webhook provider -> billing handlers; tenant -> owner control plane; jobs -> tenant data; AI tools -> external integrations.

## Threats and mitigations
- **Cross-tenant access / BOLA:** object authorization, tenant-aware predicates, negative integration tests, optionally RLS.
- **Privilege escalation:** scoped role assignment, prevent delegation beyond actor permissions, approval and audit for owner actions.
- **Plan price manipulation:** immutable published plan versions, server-side validation, contract pinning, audit and controlled effective dates.
- **Webhook spoofing/replay:** raw payload signature verification, replay/idempotency persistence, subscription lookup and reconciliation.
- **Secrets/data leakage:** managed secrets, restricted logging, encryption and scoped credentials.
- **Prompt injection/tool misuse:** explicit tool allowlists, authorization on every tool call, redaction and output validation.
- **Abusive resource consumption:** server-enforced quotas, rate limits, bounded retries and budget alerts.
- **Audit manipulation:** append-only/tamper-evident records, role-separated retention and independent monitoring.

## Review gates
Produce evidence from SAST, dependency/secret scans, authorization tests, threat-model review, incident drills and backup restore. Unresolved critical or high-risk findings block release.
