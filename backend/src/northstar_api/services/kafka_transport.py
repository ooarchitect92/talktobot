"""Consistent encrypted Kafka configuration for every producer and consumer."""

from __future__ import annotations

import ssl
from typing import Any

from northstar_api.config import get_settings


def kafka_transport_options() -> dict[str, Any]:
    settings = get_settings()
    protocol = settings.kafka_security_protocol
    if settings.app_env in {"staging", "production"} and protocol == "PLAINTEXT":
        raise ValueError("Deployed Kafka connections require TLS")
    options: dict[str, Any] = {"security_protocol": protocol}
    if protocol != "PLAINTEXT":
        options["ssl_context"] = ssl.create_default_context()
    if protocol == "SASL_SSL":
        if not settings.kafka_sasl_username or not settings.kafka_sasl_password:
            raise ValueError("Kafka SCRAM credentials are required")
        options.update(
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username=settings.kafka_sasl_username,
            sasl_plain_password=settings.kafka_sasl_password.get_secret_value(),
        )
    return options
