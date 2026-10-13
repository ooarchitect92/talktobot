from pathlib import Path

import yaml
from celery import Celery

ROOT = Path(__file__).resolve().parents[2]


def test_managed_broker_worker_uses_compatible_queues_and_checks_consumption():
    deployment = yaml.safe_load((ROOT / "kubernetes/base/worker.yaml").read_text(encoding="utf-8"))
    worker = deployment["spec"]["template"]["spec"]["containers"][0]
    command = worker["command"]
    selected = next(argument for argument in command if argument.startswith("--queues="))
    queues = selected.split("=", 1)[1].split(",")
    assert len(queues) <= 10
    assert {"ingest.source", "operations", "telegram.outbound"} <= set(queues)
    assert not any(queue.endswith(".failed") for queue in queues)
    app = Celery("deployment-validation")
    app.config_from_cmdline(
        [argument for argument in command if "_queue_exclusive=" in argument], namespace="worker"
    )
    assert app.conf.control_queue_exclusive
    assert app.conf.event_queue_exclusive
    assert not app.conf.control_queue_durable
    probe = worker["readinessProbe"]["exec"]["command"][-1]
    assert "inspect(destination=" in probe and "assert" in probe and ".ping()" in probe
