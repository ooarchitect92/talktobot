# Current state — TalkToBot

Source: `main` inspected on 2026-10-13 through the GitHub repository tree and selected source files. This is an initial architectural inventory, **not** a completed security or runtime audit.

## Verified stack
- Backend: Python 3.12+ / FastAPI / SQLAlchemy async / Alembic; see `backend/pyproject.toml`.
- Frontend: `frontend/src/app/routes.tsx`, React/TypeScript feature modules, owner/admin screens under `frontend/src/features/super-admin` and `platform-admin`.
- Persistence/infrastructure: PostgreSQL access via SQLAlchemy and asyncpg; Redis, Celery, Kafka, S3 and deployment manifests have repository evidence. Operational configuration remains to be verified.
- Delivery: CI, security and staging/production workflows exist under `.github/workflows`; passing behavior has not been verified.

## Reusable code verified
- `backend/src/northstar_api/subscriptions.py`: tenant subscription persistence and lifecycle fields.
- `backend/src/northstar_api/entitlements.py`: plan entitlements with hardcoded plan catalog.
- `backend/src/northstar_api/routers/billing.py`: billing endpoints, permission dependencies and Stripe integration.
- `backend/src/northstar_api/modules/workspace/services/role_service.py`: workspace custom-role validation and cross-workspace guards.
- `backend/src/northstar_api/modules/platform_admin/api/control_plane.py`: compatibility adapter to the existing super-admin control plane.
- Existing tests include `backend/tests/test_subscriptions.py`, `test_entitlements.py`, `test_platform_admin_permissions.py`, `test_stripe_billing_provider.py` and role tests.

## Unverified
No tests, builds, migrations, load tests, live payment reconciliation or production recovery drills were executed in this phase. Results must remain unscored until independently tested.
