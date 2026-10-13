# ruff: noqa: S603
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_public_staging_requires_explicit_mode_and_known_hosts(tmp_path):
    ingress = tmp_path / "ingress.yaml"
    ingress.write_text(
        (ROOT / "kubernetes/overlays/staging/ingress.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/set-staging-ingress-access.py"), str(ingress), "--public"],
        check=True,
    )
    annotations = yaml.safe_load(ingress.read_text(encoding="utf-8"))["metadata"]["annotations"]
    assert not any(key.startswith("alb.ingress.kubernetes.io/conditions.") for key in annotations)
    spec = importlib.util.spec_from_file_location(
        "callback_public", ROOT / "scripts/prepare-staging-callback-access.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = [
        {"Actions": [{"Type": "forward"}], "Conditions": [{"Field": "host-header", "Values": [host]}]}
        for host in ("app.staging.talktobot.com", "staging.talktobot.com", "api.staging.talktobot.com")
    ]
    default = {
        "IsDefault": True,
        "Actions": [{"Type": "fixed-response", "FixedResponseConfig": {"StatusCode": "404"}}],
    }
    assert module.public_staging_rules([*rules, default])
    assert not module.public_staging_rules(rules)
    assert not module.public_staging_rules(
        [*rules, default, {"Actions": [{"Type": "forward"}], "Conditions": []}]
    )
    rules[0]["Conditions"].append({"Field": "source-ip", "SourceIpConfig": {"Values": ["1.1.1.1/32"]}})
    assert not module.public_staging_rules([*rules, default])


def test_live_listener_verification_rejects_any_unrestricted_application_rule():
    spec = importlib.util.spec_from_file_location(
        "callback_access", ROOT / "scripts/prepare-staging-callback-access.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    allowed = {"1.1.1.1/32"}
    private = {
        "Actions": [{"Type": "forward"}],
        "Conditions": [{"Field": "source-ip", "SourceIpConfig": {"Values": list(allowed)}}],
    }
    callback = {
        "Actions": [{"Type": "forward"}],
        "Conditions": [
            {"Field": "path-pattern", "Values": ["/api/v1/crm/oauth/zoho/callback"]},
            {"Field": "host-header", "Values": ["api.staging.talktobot.com"]},
        ],
    }
    assert module.protected_rules([private] * 4 + [callback], allowed)
    unrestricted = {
        "Actions": [{"Type": "forward"}],
        "Conditions": [{"Field": "path-pattern", "Values": ["/*"]}],
    }
    assert not module.protected_rules([private] * 4 + [callback, unrestricted], allowed)


def test_public_callback_rules_preserve_private_application_access(tmp_path):
    ingress = tmp_path / "ingress.yaml"
    ingress.write_text(
        (ROOT / "kubernetes/overlays/staging/ingress.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/set-staging-ingress-access.py"),
            str(ingress),
            "--cidrs",
            "8.8.8.8/32,1.1.1.1/32",
        ],
        check=True,
    )  # noqa: S603
    value = yaml.safe_load(ingress.read_text(encoding="utf-8"))
    annotations = value["metadata"]["annotations"]
    assert annotations["alb.ingress.kubernetes.io/inbound-cidrs"] == "0.0.0.0/0"
    public_paths = []
    for rule in value["spec"]["rules"]:
        for route in rule["http"]["paths"]:
            service = route["backend"]["service"]["name"]
            if service == "api-public-callback":
                assert rule["host"] == "api.staging.talktobot.com"
                public_paths.append(route["path"])
            else:
                condition = json.loads(annotations[f"alb.ingress.kubernetes.io/conditions.{service}"])
                assert condition == [
                    {"field": "source-ip", "sourceIpConfig": {"values": ["1.1.1.1/32", "8.8.8.8/32"]}}
                ]
    assert set(public_paths) == {"/api/v1/crm/oauth/zoho/callback", "/api/v1/webhooks/channels"}


def test_operator_access_cannot_be_widened_to_all_addresses(tmp_path):
    ingress = tmp_path / "ingress.yaml"
    original = (ROOT / "kubernetes/overlays/staging/ingress.yaml").read_text(encoding="utf-8")
    ingress.write_text(original, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/set-staging-ingress-access.py"),
            str(ingress),
            "--cidrs",
            "0.0.0.0/0",
        ],
        capture_output=True,
    )  # noqa: S603
    assert result.returncode != 0
    assert ingress.read_text(encoding="utf-8") == original
