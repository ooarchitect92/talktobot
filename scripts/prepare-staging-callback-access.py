"""Install and verify private listener conditions before exposing provider callbacks."""

import argparse
import ipaddress
import json
import subprocess
import time


def run(arguments):
    return subprocess.check_output(arguments, text=True)


def aws(*arguments):
    return json.loads(run(["aws", "--region", "ap-south-1", *arguments, "--output", "json"]))


def protected_rules(rules, allowed):
    public = {
        "/api/v1/crm/oauth/zoho/callback",
        "/api/v1/webhooks/channels",
        "/api/v1/webhooks/channels/*",
    }
    private_count = 0
    for rule in rules:
        if not any(action["Type"] == "forward" for action in rule["Actions"]):
            if rule.get("IsDefault") and not any(action["Type"] == "fixed-response" for action in rule["Actions"]):
                return False
            continue
        conditions = {item["Field"]: item for item in rule["Conditions"]}
        sources = set(conditions.get("source-ip", {}).get("SourceIpConfig", {}).get("Values", []))
        if sources == allowed:
            private_count += 1
            continue
        paths = set(conditions.get("path-pattern", {}).get("Values", []))
        hosts = set(conditions.get("host-header", {}).get("Values", []))
        if sources or not paths or not paths <= public or hosts != {"api.staging.talktobot.com"}:
            return False
    return private_count >= 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cidrs", required=True)
    parser.add_argument("--kubeconfig")
    args = parser.parse_args()
    networks = {ipaddress.ip_network(item.strip()) for item in args.cidrs.split(",")}
    if not networks or len(networks) > 3 or any(item.version != 4 or item.prefixlen != 32 or not item.network_address.is_global for item in networks):
        raise SystemExit("Expected up to three explicit public operator/NAT IPv4 /32 addresses")
    allowed = {str(item) for item in networks}
    if aws("sts", "get-caller-identity")["Account"] != "510439383733":
        raise RuntimeError("Unexpected AWS account")
    kubectl = ["kubectl", *(["--kubeconfig", args.kubeconfig] if args.kubeconfig else []), "-n", "northstar"]
    condition = json.dumps([{"field": "source-ip", "sourceIpConfig": {"values": sorted(allowed)}}], separators=(",", ":"))
    run([*kubectl, "annotate", "ingress", "northstar", "--overwrite",
         *[f"alb.ingress.kubernetes.io/conditions.{service}={condition}" for service in ("api", "northstar-web", "website")]])
    load_balancer = aws("elbv2", "describe-load-balancers", "--names", "k8s-northsta-northsta-907d62e7b5")["LoadBalancers"][0]
    listeners = aws("elbv2", "describe-listeners", "--load-balancer-arn", load_balancer["LoadBalancerArn"])["Listeners"]
    listener = next(item for item in listeners if item["Port"] == 443)
    for _ in range(60):
        rules = aws("elbv2", "describe-rules", "--listener-arn", listener["ListenerArn"])["Rules"]
        if protected_rules(rules, allowed):
            print("AWS HTTPS listener protects every application route; callback exposure may proceed.")
            return
        time.sleep(2)
    raise RuntimeError("Private listener conditions did not reconcile; callback exposure was not authorized")


if __name__ == "__main__":
    main()
