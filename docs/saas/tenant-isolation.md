# Tenant isolation controls and acceptance tests

## Existing evidence
`backend/src/northstar_api/modules/workspace/services/role_service.py` validates assigned member and agent IDs using both tenant and workspace predicates. `backend/src/northstar_api/services/entitlements.py` scopes usage queries by tenant. These are local controls, not evidence of complete isolation across the entire API.

## Requirements
- Derive tenant identity from authenticated membership and validated workspace context, never trust arbitrary browser-supplied tenant IDs.
- Require tenant and object-level authorization for read, create, update, export, background jobs and webhooks.
- Database queries for tenant-owned entities must include tenant context; add PostgreSQL RLS where compatible with existing session security model.
- Deny platform-owner cross-tenant access unless explicitly authorized, auditable and time-limited.
- Keep credentials, vector retrieval namespaces, object-storage keys, caches and queues tenant-scoped.
- Restrict exports, audit searches, webhooks and support impersonation to approved scopes.

## Tests to implement and run
1. Tenant A session reads, modifies, lists and exports Tenant B resources: denied.
2. Forged tenant ID in headers/body/query/path cannot widen membership.
3. User with workspace role may not delegate permissions they lack.
4. Agent/resource selected in a custom role from another workspace: rejected.
5. Tenant-specific plan override cannot affect a different tenant.
6. Background worker jobs verify tenant context and reject cross-tenant payload references.
7. Audit and analytics endpoints do not leak other tenants' events.
8. Cache and vector retrieval never cross tenant namespaces.

Do not certify isolation until endpoint-level and database-level tests pass in staging.
