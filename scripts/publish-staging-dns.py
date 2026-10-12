"""Publish only the staging aliases after verifying their ALB and private cluster."""
import json
import subprocess
import time

ZONE = "Z01959122AJ0T89VNTDTS"
HOSTS = ("staging.talktobot.com", "app.staging.talktobot.com", "api.staging.talktobot.com")


def aws(*arguments):
    return json.loads(subprocess.check_output(["aws", "--region", "ap-south-1", *arguments, "--output", "json"]))


def main():
    if aws("sts", "get-caller-identity")["Account"] != "510439383733":
        raise RuntimeError("Unexpected staging AWS account")
    cluster = aws("eks", "describe-cluster", "--name", "talktobot-staging")["cluster"]
    host = None
    for _ in range(60):
        ingress = json.loads(subprocess.check_output(["kubectl", "get", "ingress", "northstar", "-n", "northstar", "-o", "json"]))
        configured = {rule["host"] for rule in ingress["spec"]["rules"]}
        if configured != set(HOSTS):
            raise RuntimeError("Unexpected staging ingress domains")
        addresses = ingress.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        if addresses and addresses[0].get("hostname"):
            host = addresses[0]["hostname"]
            break
        time.sleep(5)
    if not host:
        raise RuntimeError("Staging ALB address not ready")
    for _ in range(60):
        matches = [lb for lb in aws("elbv2", "describe-load-balancers")["LoadBalancers"] if lb["DNSName"] == host]
        if len(matches) != 1:
            raise RuntimeError("Staging ingress load balancer not found")
        lb = matches[0]
        if (lb["VpcId"] != cluster["resourcesVpcConfig"]["vpcId"] or lb["Type"] != "application"
                or lb["Scheme"] != "internet-facing"):
            raise RuntimeError("Unexpected staging load balancer isolation")
        if lb["State"]["Code"] == "active":
            break
        if lb["State"]["Code"] != "provisioning":
            raise RuntimeError("Staging load balancer failed provisioning")
        time.sleep(5)
    else:
        raise RuntimeError("Staging load balancer did not become active")
    changes = [{"Action": "UPSERT", "ResourceRecordSet": {"Name": name, "Type": "A", "AliasTarget": {
        "HostedZoneId": lb["CanonicalHostedZoneId"], "DNSName": host, "EvaluateTargetHealth": True,
    }}} for name in HOSTS]
    result = aws("route53", "change-resource-record-sets", "--hosted-zone-id", ZONE,
                 "--change-batch", json.dumps({"Changes": changes}))
    subprocess.run(["aws", "route53", "wait", "resource-record-sets-changed", "--id", result["ChangeInfo"]["Id"]], check=True)
    print("The three isolated staging DNS aliases are in sync.")


if __name__ == "__main__":
    main()
