# TalkToBot.com staging DNS

The user confirmed `talktobot.com` on 2026-10-12. AWS identity was verified as
account `510439383733`. Terraform created three DNS/certificate resources with
no changes or deletions to existing infrastructure.

The public Route 53 zone is `staging.talktobot.com`, ID `Z01959122AJ0T89VNTDTS`.
In GoDaddy, open **talktobot.com → DNS → DNS Records → Add New Record** and add:

| Type | Name | Value | TTL |
|---|---|---|---|
| NS | staging | ns-931.awsdns-52.net | 1 hour |
| NS | staging | ns-1549.awsdns-01.co.uk | 1 hour |
| NS | staging | ns-143.awsdns-17.com | 1 hour |
| NS | staging | ns-1030.awsdns-00.org | 1 hour |

Keep the existing GoDaddy `@` nameservers and email records. These four records
delegate only the staging subdomain. The retained `.io` zone's nameservers do
not belong in this `.com` configuration.

AWS ACM has a DNS-validation CNAME in this zone for `staging.talktobot.com` and
`*.staging.talktobot.com`. Certificate status is pending validation until the
GoDaddy delegation is saved and publicly resolvable. Certificate ARN:
`arn:aws:acm:ap-south-1:510439383733:certificate/04cd6697-9b51-4eea-b573-eae1b047525b`.
Use Terraform's `staging_com_nameservers` and `staging_com_certificate_arn`
outputs for these new resources. The old outputs describe the retained `.io`
resources.

Staging ingress and callback/CORS configuration now use `.com`. DNS delegation
does not deploy the application or remove the release security blockers. Root
production DNS and production hosting are separate from this staging setup.

After delegation, verify public NS resolution, ACM issuance and the actual
load-balancer destination before adding application records. The current
Nginx ingress expects a Kubernetes TLS secret; an ACM certificate must be
attached to a compatible AWS TLS termination path before it can serve HTTPS.

References: [GoDaddy NS records](https://www.godaddy.com/en-uk/help/add-an-ns-record-19212)
and [AWS subdomain delegation](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/MigratingSubdomain.html).
