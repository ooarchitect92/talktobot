# Subscription and entitlement migration specification

## Existing implementation verified
- `backend/src/northstar_api/entitlements.py` defines frozen `PlanEntitlement` and a static `PLAN_ENTITLEMENTS` catalogue. Unknown plans resolve to a denied policy; legacy custom-contract compatibility remains.
- `backend/src/northstar_api/services/entitlements.py` checks subscription states, channels, features and capacity. It uses PostgreSQL transaction-scoped advisory locks for capacity checks.
- `backend/src/northstar_api/services/subscriptions.py` handles lifecycle, guards provider-backed cancellation and updates tenant plan compatibility state.
- `backend/tests/test_entitlements.py` already covers several plan and subscription constraints. Preserve these tests.

## Safe target migration
1. Introduce additive tables for plan definitions, immutable published plan versions, effective-dated plan prices and versioned entitlements. Do not delete the static catalogue yet.
2. Backfill existing plans and verify exact entitlements against existing snapshots.
3. Add an internal plan resolver with explicit source/version, owner authorization, cache invalidation and safe fallback. Do not infer paid entitlement from client-provided plan names.
4. Resolve tenant subscription -> pinned version -> effective entitlements, plus audited time-bounded overrides. Keep current billing capability flags and staging access semantics explicitly tested.
5. Enforce server-side entitlements in every route/worker; frontend visibility is only presentation.
6. Price edits create new versions instead of modifying customer contract prices. Require effective date, currency, tax behavior and upgrade/downgrade policy.
7. Use provider-signed, idempotent webhook handling; keep payment reconciliation separate from entitlement calculation.
8. Backwards-compatible rollout: shadow comparison, guarded read switch, rollback switch, then retirement of static resolver after evidence review.

## Mandatory verification
- Old tenants retain their existing policy through migration; unknown plans fail closed.
- Tenant A can never read or change Tenant B's plan or override.
- Concurrent capacity requests cannot exceed limits.
- Cancelled/suspended subscriptions cannot create plan-gated resources.
- Expired overrides cease automatically.
- Published plans and active contract prices cannot be silently edited.
- Duplicate webhooks cannot mutate subscriptions twice.
- Any discrepancies in shadow comparison block rollout.
