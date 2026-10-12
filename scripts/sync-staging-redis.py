"""Apply only the Redis URL from AWS Secrets Manager; never print credentials."""
from __future__ import annotations

import argparse
import json
import subprocess
from urllib.parse import urlsplit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aws", default="aws")
    parser.add_argument("--profile")
    parser.add_argument("--kubeconfig", required=True)
    args = parser.parse_args()
    command = [args.aws, "--region", "ap-south-1", "--no-cli-pager"]
    if args.profile:
        command += ["--profile", args.profile]

    def aws(*parameters: str) -> dict:
        result = subprocess.run(command + list(parameters) + ["--output", "json"],
                                capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError("AWS lookup failed; check authentication and permissions")
        return json.loads(result.stdout)

    if aws("sts", "get-caller-identity")["Account"] != "510439383733":
        raise RuntimeError("Unexpected AWS account")
    cluster = aws("eks", "describe-cluster", "--name", "talktobot-staging")["cluster"]
    config = subprocess.run(["kubectl", "--kubeconfig", args.kubeconfig, "config", "view",
                             "--minify", "--raw", "-o", "json"], capture_output=True, check=True)
    configured_cluster = json.loads(config.stdout)["clusters"][0]["cluster"]
    if configured_cluster.get("certificate-authority-data") != cluster["certificateAuthority"]["data"]:
        raise RuntimeError("Kubeconfig does not belong to the staging cluster")
    secret = aws("secretsmanager", "get-secret-value", "--secret-id", "talktobot/staging/application")
    url = json.loads(secret["SecretString"])["REDIS_URL"]
    parsed = urlsplit(url)
    redis = aws("elasticache", "describe-replication-groups", "--replication-group-id", "talktobot-staging")
    endpoint = redis["ReplicationGroups"][0]["NodeGroups"][0]["PrimaryEndpoint"]["Address"]
    if parsed.scheme != "rediss" or parsed.hostname != endpoint or not parsed.password or parsed.query:
        raise RuntimeError("Redis secret does not match the verified TLS staging endpoint")
    document = {"apiVersion": "v1", "kind": "Secret", "metadata": {
        "name": "northstar-secrets", "namespace": "northstar"}, "type": "Opaque",
        "stringData": {"REDIS_URL": url}}
    result = subprocess.run(["kubectl", "--kubeconfig", args.kubeconfig, "apply", "--server-side",
                             "--field-manager=talktobot-redis", "-f", "-"],
                            input=json.dumps(document).encode(), capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("Redis secret application failed; check namespace, ownership and permissions")
    print("Staging Redis secret synchronized; credentials were not written to disk or logs.")


if __name__ == "__main__":
    main()
