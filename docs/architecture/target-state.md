# Target SaaS architecture

Preserve the existing FastAPI/React/SQLAlchemy stack. Do not replace it with a separate TypeScript backend.

## Control plane
Owner-admin APIs and UI manage tenant directory, plan catalogue, immutable published plan versions, effective-dated prices, subscription assignments, tenant overrides, privileged audits and billing operations.

## Tenant runtime
Tenant-authenticated APIs use a single entitlement evaluation contract combining subscription status, plan version, approved overrides, feature dependency policies, remaining quotas and user permissions. Enforce on the backend and deny safely if authorization context cannot be established.

## Delivery boundaries
- Tenant-owned database rows remain scoped to validated tenant identity; test tenant isolation end-to-end.
- Payments use provider-signed webhooks, event idempotency and reconciliation; billing prices are not retroactively mutated.
- Every privileged configuration mutation generates an auditable event with redacted sensitive fields.
- Keep existing frontend and backend endpoints compatible while migrating static entitlements to versioned data-backed entitlements.
- Add migrations, deterministic tests, load testing and recovery validation before any production launch.

## Incremental rollout
1. Full source and runtime audit; baseline metrics.
2. Immutable catalogue/price version models behind feature flag.
3. Owner APIs with authorization and audit logging.
4. Owner UI, tenant entitlements and targeted integration tests.
5. Billing lifecycle/reconciliation hardening, broader security and release gates.

No direct production deployment without independently verified release criteria.
