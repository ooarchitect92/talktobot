from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_OVERRIDE = _ROOT / "compose.override.yaml"
_KUBERNETES_MIGRATION = _ROOT / "kubernetes" / "base" / "migration.yaml"


def test_default_compose_migration_override_upgrades_all_heads() -> None:
    content = _COMPOSE_OVERRIDE.read_text(encoding="utf-8")
    start = content.index("  migrate:\n")
    end = content.index("\n  notification-consumer:\n", start)
    migrate_block = content[start:end]

    command = yaml.safe_load("services:\n" + migrate_block)["services"]["migrate"]["command"]
    assert command[:2] == ["sh", "-ec"]
    assert command[2].split("&&")[0].strip().split() == ["alembic", "upgrade", "heads"]
    assert "python -m northstar_api.workers.help_content_sync" in command[2]


def test_kubernetes_migration_job_upgrades_all_heads() -> None:
    content = _KUBERNETES_MIGRATION.read_text(encoding="utf-8")

    job = yaml.safe_load(content)
    container = job["spec"]["template"]["spec"]["containers"][0]
    command = container["command"]
    assert command[:2] == ["sh", "-ec"]
    steps = [step.strip().split() for step in command[2].split("&&")]
    assert steps[0] == ["alembic", "upgrade", "heads"]
    assert steps[1] == ["python", "-m", "northstar_api.workers.help_content_sync"]
    assert container["env"][0]["valueFrom"]["secretKeyRef"] == {
        "name": "northstar-migration-secrets",
        "key": "DATABASE_URL",
    }
