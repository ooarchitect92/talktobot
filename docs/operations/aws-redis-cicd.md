# AWS Redis and delivery configuration

Source repository: `ooarchitect92/talktobot`. Region: Mumbai (`ap-south-1`). Staging account: `510439383733`; cluster: `talktobot-staging`.

## Redis

The private ElastiCache replication group uses TLS, authentication, encrypted storage and seven-day snapshots. It currently has one cache node; automatic failover and production high availability are not qualified. Its authentication token and complete `REDIS_URL` live in `talktobot/staging/application` in AWS Secrets Manager. The application requires `rediss://`, authentication and certificate/hostname verification in staging and production. Redis failures cannot fall back to local memory there. Redis coordinates rate limits, single-use authentication purposes and refresh-token families; RabbitMQ remains the durable Celery broker.

`scripts/sync-staging-redis.py` validates the AWS account, staging cluster CA and actual ElastiCache endpoint before applying only the Redis key to `northstar-secrets`. Secret values stay in process memory and stdin, without files or log output. Bootstrap the `northstar` namespace separately with operator credentials; populate the remaining application secrets and least-privilege database credentials before deployment. This command does not deploy the application or restart existing pods.

## CI and CD

CI checks backend types/tests/formatting, frontend and website quality, real Redis concurrency, Terraform validation, Kubernetes rendering and security scans. The checksum-verified Gitleaks CLI version is shared by CI and release verification. HIGH/CRITICAL source vulnerabilities are blocked even without an available fix.

Release verification publishes three digest-addressed images with provenance. Staging deployment verifies their attestations and uses short-lived AWS OIDC credentials. Its trust subject is exactly `repo:ooarchitect92@274523797/talktobot@1415168926:environment:staging`; audience is `sts.amazonaws.com`. The deployment role can describe only the staging cluster, read the staging application secret, decrypt it only through Secrets Manager, inspect Redis configuration and edit Kubernetes resources only in `northstar`. Secrets Manager permissions apply to the entire application secret, so runner and environment access must be restricted.

Staging CD requires a self-hosted Linux runner labeled `talktobot-staging` inside the approved private-network boundary, with AWS CLI, kubectl, Python, Docker/buildx, gh and jq available. Never route untrusted pull-request jobs to this runner. No such runner is registered yet. GitHub-hosted runners cannot directly reach the private EKS endpoint. Operator bootstrap and environment review controls remain prerequisites.

GitHub staging variables: `AWS_DEPLOY_ROLE_ARN=arn:aws:iam::510439383733:role/talktobot-staging-github-deploy`, `EKS_CLUSTER_NAME=talktobot-staging`. Do not configure production with this staging role. Production requires a separately approved account/infrastructure configuration and role.

## Evidence and remaining gates

Local configuration/Redis checks: 23 passed, including 100 concurrent single-use claims and concurrent refresh rotation/replay revocation. Backend strict types: 453 source files passed. Concurrency testing used an authenticated local Redis instance. A separate authenticated PING passed against AWS ElastiCache through an SSM tunnel, with certificate and hostname verification; the temporary tunnel was terminated afterward. Terraform and staging manifests validate. Application rollouts, DNS/HTTPS, private runner registration, provider credentials, full passing CI, AWS Redis outage/failover acceptance, recovery, load and soak evidence remain required. The latest remote CI failed; do not describe this as a passing or deployed release.
