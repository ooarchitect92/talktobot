"""Validate new Workspace custom-domain hostnames without rewriting legacy records.

The existing DomainRecord parser remains compatible with already-persisted
settings; stricter validation applies only at the new-domain creation boundary.
"""

from __future__ import annotations

import ipaddress
import re

from sqlalchemy.exc import IntegrityError

_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", flags=re.ASCII)
_INVALID_HOSTNAME = "Enter a DNS hostname such as portal.customer.com (no scheme, port, path or wildcard)"


def normalize_new_custom_domain_hostname(value: str) -> str:
    """Return an ASCII DNS hostname, allowing one optional trailing root dot.

    An IP address, a local single-label name, or a string with URL syntax is
    not a custom domain suitable for TXT verification and branded HTTPS.
    Internationalized domain names can be supplied in ASCII/Punycode form.
    """
    normalized = value.strip().lower()
    if normalized.endswith("."):
        normalized = normalized[:-1]
    labels = normalized.split(".")
    if (
        len(normalized) > 253
        or len(labels) < 2
        or len(labels[-1]) < 2
        or any(_DNS_LABEL.fullmatch(label) is None for label in labels)
    ):
        raise ValueError(_INVALID_HOSTNAME)
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        return normalized
    raise ValueError("Use a DNS hostname instead of an IP address")


__all__ = ["normalize_new_custom_domain_hostname"]


def is_hostname_unique_violation(exc: IntegrityError) -> bool:
    """Recognize only the domain hostname constraint, not unrelated SQL errors."""
    orig = exc.orig
    diagnostic = getattr(orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    if constraint == "uq_workspace_custom_domain_hostname":
        return True
    message = str(orig).lower()
    return (
        "uq_workspace_custom_domain_hostname" in message
        or "unique constraint failed: workspace_custom_domain.hostname" in message
    )
