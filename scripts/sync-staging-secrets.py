"""Synchronize private staging credentials without files or credential logging."""
from __future__ import annotations

import argparse
import json
import subprocess
from urllib.parse import parse_qs, quote, urlsplit


RUNTIME_KEYS = (
    "DATABASE_URL", "REDIS_URL", "RABBITMQ_URL", "JWT_SECRET", "MFA_ENCRYPTION_KEY",
    "CRM_CREDENTIAL_ENCRYPTION_KEY", "WEBSITE_PROXY_SECRET", "KAFKA_SASL_USERNAME",
    "KAFKA_SASL_PASSWORD",
)
PROVIDER_KEYS = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_STARTTLS",
    "SMTP_SSL", "EMAIL_FROM_ADDRESS", "EMAIL_FROM_NAME", "EMAIL_DELIVERY_MODE", "NVIDIA_API_KEY",
)


def build_documents(application: dict, providers: dict, migration_url: str) -> list[dict]:
    runtime = {}
    for source, keys in ((application, RUNTIME_KEYS), (providers, PROVIDER_KEYS)):
        for key in keys:
            value = source.get(key)
            if not isinstance(value, str) or not value:
                raise RuntimeError(f"Required staging setting missing: {key}")
            runtime[key] = value
    # Master credentials never enter the API or worker environment.
    return [
        {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": "northstar"},
         "type": "Opaque", "stringData": values}
        for name, values in (
            ("northstar-secrets", runtime),
            ("northstar-worker-secrets", {"DATABASE_URL": application["WORKER_DATABASE_URL"]}),
            ("northstar-migration-secrets", {"DATABASE_URL": migration_url}),
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws", default="aws")
    parser.add_argument("--profile")
    parser.add_argument("--kubeconfig", required=True)
    args = parser.parse_args()
    command = [args.aws, "--region", "ap-south-1", "--no-cli-pager"]
    if args.profile:
        command += ["--profile", args.profile]

    def aws(*parameters: str) -> dict:
        result = subprocess.run(command + list(parameters) + ["--output", "json"], capture_output=True)
        if result.returncode:
            raise RuntimeError("Staging AWS lookup failed; check authentication and permissions")
        return json.loads(result.stdout)

    def secret(name: str) -> dict:
        return json.loads(aws("secretsmanager", "get-secret-value", "--secret-id", name)["SecretString"])

    if aws("sts", "get-caller-identity")["Account"] != "510439383733":
        raise RuntimeError("Unexpected AWS account")
    cluster = aws("eks", "describe-cluster", "--name", "talktobot-staging")["cluster"]
    config = subprocess.run(
        ["kubectl", "--kubeconfig", args.kubeconfig, "config", "view", "--minify", "--raw", "-o", "json"],
        capture_output=True, check=True,
    )
    configured = json.loads(config.stdout)["clusters"][0]["cluster"]
    if configured.get("certificate-authority-data") != cluster["certificateAuthority"]["data"]:
        raise RuntimeError("Kubeconfig does not belong to staging")
    database = aws("rds", "describe-db-instances", "--db-instance-identifier", "talktobot-staging")["DBInstances"][0]
    if (database["DBSubnetGroup"]["VpcId"] != cluster["resourcesVpcConfig"]["vpcId"]
            or database["PubliclyAccessible"] or not database["StorageEncrypted"]):
        raise RuntimeError("Unexpected staging database isolation")
    application = secret("talktobot/staging/application")
    providers = secret("talktobot/staging/providers")
    parsed = urlsplit(application["DATABASE_URL"])
    if (parsed.hostname != database["Endpoint"]["Address"] or parsed.username != "talktobot_runtime"
            or parse_qs(parsed.query) != {"ssl": ["verify-full"]}):
        raise RuntimeError("Staging database URL must use its restricted role and verified TLS")
    worker = urlsplit(application["WORKER_DATABASE_URL"])
    if (worker.hostname != database["Endpoint"]["Address"] or worker.username != "northstar_service"
            or parse_qs(worker.query) != {"ssl": ["verify-full"]}):
        raise RuntimeError("Staging workers require their separate service identity and verified TLS")
    redis = aws("elasticache", "describe-replication-groups", "--replication-group-id", "talktobot-staging")
    endpoint = redis["ReplicationGroups"][0]["NodeGroups"][0]["PrimaryEndpoint"]["Address"]
    parsed = urlsplit(application["REDIS_URL"])
    if parsed.scheme != "rediss" or parsed.hostname != endpoint or not parsed.password or parsed.query:
        raise RuntimeError("Unexpected staging Redis TLS configuration")
    master = secret(database["MasterUserSecret"]["SecretArn"])
    migration_url = (f"postgresql+asyncpg://{quote(master['username'], safe='')}:{quote(master['password'], safe='')}"
                     f"@{database['Endpoint']['Address']}:5432/talktobot?ssl=verify-full")
    for document in build_documents(application, providers, migration_url):
        result = subprocess.run(
            ["kubectl", "--kubeconfig", args.kubeconfig, "apply", "--server-side",
             "--field-manager=talktobot-secrets", "-f", "-"],
            input=json.dumps(document).encode(), capture_output=True,
        )
        if result.returncode:
            raise RuntimeError("Staging secret synchronization failed; inspect access and field ownership")
    print("Staging runtime and separate migration secrets synchronized; values were not logged.")


if __name__ == "__main__":
    main()
