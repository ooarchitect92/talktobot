# Deployment repository

The deployment source is https://github.com/ooarchitect92/talktobot, branch `main`.
This repository starts with a single initial snapshot. The workspace has no retained legacy Git objects or remotes; old issue and CI links in documents describe historical evidence only.

A push to main runs CI. The release workflow must pass its verification gates before publishing the API, application and website images under `ghcr.io/ooarchitect92/talktobot-{api,web,website}`. The deployment workflow checks image attestations against this repository and the selected full commit SHA, and deploys by digest. A source push does not launch production.

Before running a release, configure the repository variable `S3_PUBLIC_ENDPOINT_URL` with the verified HTTPS media origin. The production environment requires `AWS_DEPLOY_ROLE_ARN` and `EKS_CLUSTER_NAME`, separately approved production infrastructure, environment reviewers and branch restrictions. Configure the AWS OIDC trust subject as `repo:ooarchitect92@274523797/talktobot@1415168926:environment:production`, with audience `sts.amazonaws.com`; use least-privilege deployment permissions. No long-lived AWS credentials belong in GitHub or Git.

The existing staging EKS API is private. Deployment needs a runner with authorized network access; the public GitHub-hosted runner cannot reach that endpoint directly. Staging deployment and production promotion remain subject to the gates in [release qualification](release-qualification.md).

Do not store application secrets, local .env files, Terraform plans/state, credentials, or private inventory snapshots in this public repository. Supply workload secrets through the approved AWS secret-management path.

AWS Redis, OIDC, private staging runner requirements and remaining acceptance gates are detailed in [AWS Redis and delivery configuration](aws-redis-cicd.md).
