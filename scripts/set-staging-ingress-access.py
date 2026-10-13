"""Replace the deny-by-default staging CIDR with validated operator/NAT addresses."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--cidrs", required=True)
    args = parser.parse_args()
    networks = [ipaddress.ip_network(value.strip()) for value in args.cidrs.split(",")]
    if not networks or any(network.version != 4 or network.prefixlen != 32 or not network.network_address.is_global for network in networks):
        raise SystemExit("Staging access requires explicit public IPv4 /32 operator/NAT addresses")
    replacement = ",".join(sorted({str(network) for network in networks}))
    source = args.path.read_text(encoding="utf-8")
    if "alb.ingress.kubernetes.io/conditions." in source:
        values = replacement.split(",")
        if len(values) > 3:
            raise SystemExit("ALB source-IP conditions support at most three operator/NAT addresses")
        condition = json.dumps([{"field": "source-ip", "sourceIpConfig": {"values": values}}], separators=(",", ":"))
        updated, count = re.subn(
            r"(?m)^(\s*alb\.ingress\.kubernetes\.io/conditions\.(?:api|northstar-web|website):) [^\n]+$",
            lambda match: f"{match.group(1)} '{condition}'", source,
        )
        if count != 3 or 'alb.ingress.kubernetes.io/inbound-cidrs: "0.0.0.0/0"' not in source:
            raise SystemExit("Expected source restrictions on all three private staging services")
        args.path.write_text(updated, encoding="utf-8")
        return
    updated, count = re.subn(
        r'(?m)^(\s*alb\.ingress\.kubernetes\.io/inbound-cidrs:) [^\n]+$',
        lambda match: f'{match.group(1)} "{replacement}"', source,
    )
    if count != 1:
        raise SystemExit("Expected exactly one staging ingress access declaration")
    args.path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
