# Test strategy and execution evidence

The previously inspected repository includes backend pytest suites and frontend Vitest scripts. No test execution has yet been confirmed in this audit branch.

## Baseline commands (isolated development environment)
- Backend: `cd backend && uv sync --group dev && uv run pytest -q` (verify uv availability/configuration before running).
- Backend static checks: `cd backend && uv run ruff check . && uv run mypy src`.
- Frontend: `cd frontend && npm ci && npm run lint && npm run typecheck && npm run test && npm run build`.
- Database: apply Alembic migrations against a disposable PostgreSQL database, then test downgrade/rollback behavior for new migrations.
- Security: run repository-configured Gitleaks/CodeQL and dependency scanning; record outputs.
- Billing: sandbox webhook signature, duplicate events, out-of-order events, provider/local state reconciliation.
- SaaS: cross-tenant negative tests, entitlement snapshots, owner-policy authorization, quota concurrency tests.

Capture command, commit SHA, environment, date, exit code and logs for every result. Do not convert unexecuted commands into passing claims.
