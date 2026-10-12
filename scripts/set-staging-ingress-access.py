"""Replace the deny-by-default staging CIDR with validated operator/NAT addresses."""
from __future__ import annotations

import argparse
import ipaddress
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
    updated, count = re.subn(
        r'(?m)^(\s*alb\.ingress\.kubernetes\.io/inbound-cidrs:) [^\n]+$',
        lambda match: f'{match.group(1)} "{replacement}"', source,
    )
    if count != 1:
        raise SystemExit("Expected exactly one staging ingress access declaration")
    args.path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
