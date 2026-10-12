# AWS staging and production proposal

Status: **staging approved by the user on 2026-10-12; provisioning underway**. Production remains unapproved.

Account 510439383733, region ap-south-1. The 2026-10-12 inventory found no reusable deployment in the queried EC2, EKS, ECS, RDS, cache, broker, Lambda, S3, DNS or CDN services. Three regional Lightsail queries failed and remain unverified. This does not mean the account contains no other resources.

Retain the repository's Kubernetes architecture. Use separate staging and production EKS clusters, VPCs, databases, caches, brokers, buckets, secrets and workload/deployment roles. Staging uses synthetic accounts and media exclusively. Domains are staging.talktobot.io, app.staging.talktobot.io and api.staging.talktobot.io. Domain ownership and the authoritative DNS provider still need verification.

Planning costs below assume 730 hours/month, on-demand Mumbai rates. Actual rates retrieved with AWS Price List API are retained in [aws-prices-2026-10-12.json](aws-prices-2026-10-12.json). Infrastructure sizes are initial assumptions to be qualified by load tests.

| Component | Staging | Production | Monthly USD, staging / production |
|---|---|---|---:|
| EKS standard support | 1 cluster | 1 cluster | 73 / 73 |
| EC2 Linux compute | 2 m6i.xlarge | 3 m6i.xlarge, spread across AZs | 294.92 / 442.38 |
| PostgreSQL | db.t4g.medium Single-AZ | db.t4g.medium Multi-AZ | 61.32 / 121.91 |
| RabbitMQ | mq.m7g.medium Single-AZ | mq.m5.large three-node cluster | 71.39 / 663.57 |
| Kafka | 3 kafka.t3.small brokers | 3 kafka.m7g.large brokers | 107.53 / 319.30 |
| Redis | 1 cache.t4g.small | 2 cache.t4g.small, failover | 29.93 / 59.86 |
| Network, storage, backups, logs and alerts | Budget allowance | Budget allowance | 212–412 / 320–920 |
| **Planning total** | | | **800–1,000 / 2,000–2,600** |

Combined planning allowance: **USD 2,800–3,600/month**. Allow up to USD 1,000/month for staging first; production requires a separate review after measured staging consumption. These are estimates, not spending caps. Budgets alert on spending; they do not stop services. Taxes, paid support, domain registration, AI inference, embeddings, email delivery, unusually high traffic, and extended Kubernetes/database support are excluded. Database CPU credits and backup/storage growth can add cost. Price dimensions for RabbitMQ cluster deployment already include the three-node cluster; do not multiply that rate by three again.

EKS pricing source: https://aws.amazon.com/eks/pricing/ . Storage and traffic charges: https://aws.amazon.com/vpc/pricing/ and https://aws.amazon.com/rds/postgresql/pricing/ . RDS and broker rates above come from the saved Mumbai API response.

Provisioning acceptance requires: private data services; encrypted 35-day PostgreSQL PITR; separate backup role; protected versioned S3; OIDC deploy role restricted to repository/environment; least-privilege workload roles; HTTPS; DNS control; durable queues; monitoring; and a staging-only secret inventory. No production seed credentials, customer data, or unqualified integrations may be enabled.

Operational owner and backup/on-call owner must be named before production promotion. The contact tech@northstaracad.com is recorded as a business contact, not automatically appointed as incident owner. Business approval of final legal policies remains outstanding.

Code quality failures still block qualification. Approval of this cost proposal permits infrastructure preparation only; it is not evidence that staging acceptance or production launch has passed.

Availability reconciliation: AWS currently does not offer mq.t3.micro RabbitMQ in this region despite advertising its price. Staging uses the supported mq.m7g.medium at USD 0.0978/hour, with a smaller contingency allowance to retain the approved planning range. Primary operational contact: ooarchitect92@gmail.com. Backup owner and notification delivery confirmation remain pending.


2026-10-12 staging implementation: three encrypted ECR repositories and one provider secret use the existing storage/secrets contingency allowance. The load balancer controller and network policy agent reuse the approved nodes. Hosted deployment jobs connect through a fixed-destination SSM port-forward document; no additional runner instance is provisioned. Any temporary database restore clone must have its duration/cost recorded within the approved staging allowance and be removed after evidence is collected. Production remains a separate cost review.
