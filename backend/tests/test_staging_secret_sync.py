from __future__ import annotations

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest


def sync_module() -> dict:
    return runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/sync-staging-secrets.py"))


def test_migration_credentials_never_enter_runtime_environment() -> None:
    module = sync_module()
    application = dict.fromkeys(module["RUNTIME_KEYS"], "synthetic fixture")
    application["WORKER_DATABASE_URL"] = "service fixture"
    providers = dict.fromkeys(module["PROVIDER_KEYS"], "synthetic fixture")
    application["MIGRATION_DATABASE_URL"] = "must not propagate"
    providers["MASTER_PASSWORD"] = application["JWT_SECRET"]
    documents = module["build_documents"](application, providers, "migration fixture")
    runtime, worker, migration = documents
    assert runtime["metadata"]["name"] == "northstar-secrets"
    assert "MIGRATION_DATABASE_URL" not in runtime["stringData"]
    assert "MASTER_PASSWORD" not in runtime["stringData"]
    assert "WORKER_DATABASE_URL" not in runtime["stringData"]
    assert worker["metadata"]["name"] == "northstar-worker-secrets"
    assert worker["stringData"] == {"DATABASE_URL": "service fixture"}
    assert migration["metadata"]["name"] == "northstar-migration-secrets"
    assert migration["stringData"] == {"DATABASE_URL": "migration fixture"}


def test_missing_provider_setting_fails_without_disclosing_values() -> None:
    module = sync_module()
    application = dict.fromkeys(module["RUNTIME_KEYS"], "private sentinel")
    providers = dict.fromkeys(module["PROVIDER_KEYS"], "private sentinel")
    del providers["SMTP_PASSWORD"]
    with pytest.raises(RuntimeError, match="SMTP_PASSWORD") as error:
        module["build_documents"](application, providers, "migration fixture")
    assert "private sentinel" not in str(error.value)


@pytest.mark.parametrize("wrong_account", [True, False])
def test_wrong_account_or_cluster_stops_before_secret_lookup(monkeypatch, wrong_account: bool) -> None:
    module = sync_module()
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        if "get-caller-identity" in command:
            result = {"Account": "different account" if wrong_account else "510439383733"}
        elif "describe-cluster" in command:
            result = {"cluster": {"certificateAuthority": {"data": "expected certificate"}}}
        else:
            assert command[0] == "kubectl"
            result = {"clusters": [{"cluster": {"certificate-authority-data": "different certificate"}}]}
        return SimpleNamespace(returncode=0, stdout=json.dumps(result).encode())

    monkeypatch.setattr("subprocess.run", run)
    monkeypatch.setattr("sys.argv", ["sync", "--kubeconfig", "fixture"])
    with pytest.raises(RuntimeError, match="Unexpected AWS account|does not belong to staging"):
        module["main"]()
    assert not any("get-secret-value" in command for command in calls)
