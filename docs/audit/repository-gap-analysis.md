# Preliminary SaaS gap matrix

Evidence level: **selected source inspection only**. Status labels distinguish source-confirmed implementation from capabilities requiring deeper inspection.

| Capability | Status | Evidence / next verification |
|---|---|---|
| Backend framework | Existing | `backend/pyproject.toml`: FastAPI, SQLAlchemy, Alembic |
| Frontend routes and admin UI | Reusable | `frontend/src/app/routes.tsx`, `frontend/src/features/super-admin/` and `platform-admin/`; behavior not yet verified |
| Subscription persistence | Existing | `backend/src/northstar_api/subscriptions.py` |
| Entitlement catalog | Refactor Required | `backend/src/northstar_api/entitlements.py` contains static `PLAN_ENTITLEMENTS`; determine existing runtime overrides before introducing DB-driven catalog |
| Billing | Reusable | `backend/src/northstar_api/routers/billing.py`, `services/stripe_billing.py`; verify webhook replay, event integrity and reconciliation |
| Workspace custom roles | Reusable | `modules/workspace/services/role_service.py` has delegation and workspace scoping checks; inspect callers |
| Platform owner control plane | Reusable | `modules/platform_admin/api/control_plane.py` delegates to super-admin implementation; inspect capabilities |
| Pricing versioning | Blocked — unverified | Inspect all price, plan and migration models; do not assume missing |
| Tenant-specific feature overrides | Blocked — unverified | Trace entitlement service resolution and authorization callers |
| Activity and audit | Reusable | Audit-related modules/tests exist; confirm tamper resistance and owner-level filters |
| CI / release gates | Reusable | `.github/workflows/ci.yml`, CodeQL, staging and production deployment workflows; inspect outcomes |
| Runtime, security and quality score | Blocked — unverified | Execute complete suite and inspect findings in safe test environment |

## Ordered work
1. Trace existing subscription and entitlement models, API, UI, migrations and tests end-to-end.
2. Inventory owner control plane and billing mutations.
3. Document gaps for versioned pricing/feature access, then add backwards-compatible migrations.
4. Write regression and cross-tenant security tests before replacing any entitlement resolution.
5. Benchmark test/build/migration health and publish objective quality scoring.
