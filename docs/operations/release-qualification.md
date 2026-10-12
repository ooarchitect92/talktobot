# TalkToBot release qualification

Status: **NOT QUALIFIED — public production launch blocked**.

Scope: public website, owner console, customer application, API and every enabled worker. Staging provisioning was approved on 2026-10-12 at the reviewed USD 800–1,000/month planning allowance. Production infrastructure and promotion remain unapproved.

## Evidence and limitations

| Gate | Evidence | Status |
|---|---|---|
| AWS identity | Account 510439383733, authenticated IAM user @ni | Verified |
| Staging infrastructure | Terraform main/security/recovery/DNS configuration; encrypted remote state; managed private data services; EKS API public access disabled | Provisioned |
| AWS Redis and OIDC | Private authenticated Redis TLS PING passed; 23 local Redis/config checks; staging-only OIDC role and namespace access configured | Basic connectivity verified; rollout and failover pending |
| Staging DNS / HTTPS | ACM certificate requested and staging subzone created | Pending GoDaddy details; user deferred delegation |
| Source vulnerability/secret/configuration scan | reports/readiness/trivy-source-current.json and its source-tree receipt | Zero critical/high findings for that diagnostic export; not release evidence for later edits |
| Strict backend type checking | reports/readiness/gates-20261012T113504475412Z-757e28re/backend-types.log | Passed: 453 source files; explicit strict configuration |
| Full backend tests | reports/readiness/gates-20261012T113504475412Z-757e28re/backend-tests.log | Passed: 1,701 tests, no skips; real Redis concurrency included. This worktree run changed during checks and is diagnostic, not immutable qualification. |
| Full frontend tests | reports/readiness/gates-20261012T113504475412Z-757e28re/frontend-tests.log | Passed: 624 tests, including the final application fixes. |
| Website build/server checks | reports/readiness/gates-20261012T113504475412Z-757e28re/website-*.log | Build and 8 server tests passed. |
| Frontend lint / types / build | reports/readiness/gates-20261012T113504475412Z-757e28re | All passed without disabling lint rules. |
| Read-only web startup | reports/readiness/web-proxy-smoke.json; web-image-final-scan.json | Non-root, read-only startup passes health, page, unauthenticated API denial and disabled AWS storage checks; web image has no critical/high findings. |
| Immutable commit and image digests | None qualified | Pending |
| Container scans / remote CI | reports/readiness/api-image-trixie-scan.json; website-image-patched-scan.json; web-image-final-scan.json; GitHub CI run 38245017208 | Web and patched website scans have no critical/high findings. Updated API retains 1 critical and 100 high package findings: launch blocked. Remote source, configuration, frontend and backend gates pass on bb9da0b; topology acceptance is still pending and this is not final-image qualification. |
| Restore and rollback | Infrastructure supports protected versions and 35-day database backups; dedicated recovery role exists | Actual restoration/rollback drills pending |
| Load / soak | Targets: 100 active sessions, one hour, under 1% server errors, ordinary API p95 under one second; 24-hour soak | Not run |
| Monitoring | Staging database alarms and encrypted SNS topic configured | Delivery and synthetic application checks pending |
| Independent security review | None completed | Pending |
| Controlled launch | Seven days after acceptance and approved promotion | Not started |

Earlier follow-up type checks from the repository root did not load backend/pyproject.toml and must not be treated as strict CI evidence. Use the explicit commands below. Diagnostic test runs while source files change are not qualification runs.

Primary operational contact: **ooarchitect92@gmail.com**, supplied by the user. Backup/on-call owner remains unassigned. Business identity: Northstar edtech; business contact tech@northstaracad.com. Legal policies and retention decisions still require business approval. No email or Slack messages have been sent to these contacts.

## Prelaunch fixes

The prelaunch review corrected scoped education API-key authorization, frontend asynchronous state handling and a WhatsApp number refresh that could retain an old error. Test fixtures now wait for real knowledge ingestion, assert the existing educational privacy/curriculum boundaries, select their own audit event and keep session tokens valid for the full test gate. Production token expiration and access controls were not relaxed.

The web image discovers its container DNS resolver, accepts a validated API hostname, uses the Kubernetes service FQDN in AWS and disables the Docker-only storage proxy there. Its startup writes Nginx state only under `/tmp`, supporting the existing non-root, read-only Kubernetes policy. Git enforces LF for shell scripts and the Nginx template. Source scans and test runs while files change remain diagnostic evidence.

## Runtime security blocker

The Debian 12 API image reported 7 critical and 142 high package findings. Moving its runtime to a digest-pinned Debian 13 Python image and updating packages reduced that to 1 critical and 100 high package findings. Counts are package findings, not unique vulnerabilities. The remaining findings have no fixed version listed for the installed Debian release. They have not been suppressed, accepted, or independently reviewed. In particular, [Debian's CVE-2026-6653 tracker](https://security-tracker.debian.org/tracker/CVE-2026-6653) still marks the installed libxml2 release vulnerable. Do not substitute an unstable distribution or incompatible library binary merely to obtain a clean scan.

The website runtime now pins its Node image, upgrades Alpine packages and removes npm, which the deployed server does not need. Its rebuilt runtime scan passes. The API starts successfully as a non-root user with a read-only filesystem, synthetic PostgreSQL and Redis, but this does not resolve its dependency findings.

CI now loads the explicitly scoped public-configuration exceptions, uses Trivy v0.75.0 consistently and blocks both high and critical runtime findings. Topology acceptance builds/scans the public website and checks its scheduler and HTTP routes. Release verification requires a successful complete CI run for the exact commit and includes real Redis concurrency testing. No release tag, production deployment or launch qualification was issued.

## Exact local gates

Run from the repository root with the backend environment installed:

```powershell
backend/.venv/Scripts/ruff.exe check backend
backend/.venv/Scripts/ruff.exe format --check backend
backend/.venv/Scripts/mypy.exe --config-file backend/pyproject.toml backend/src
backend/.venv/Scripts/pytest.exe backend/tests --junitxml=reports/readiness/backend-qualified.xml
npm run lint
npm run typecheck
npm test
npm run build
npm run build --prefix website
npm test --prefix website
terraform -chdir=infrastructure/staging validate
kubectl kustomize kubernetes/overlays/production
```

Freeze a commit only after local checks pass, then run CI and image scans against that same SHA. Publish and attest all enabled images, including website and scheduler. Deploy by digest; preserve previous digests and additive database compatibility. Passing a source scan cannot substitute for image scans, deployed acceptance, or an independent review.

## Provisioning incident recovery

The first Windows process stopped on native stderr handling. A later exported credential expired while EKS encryption was updating, preventing state persistence. The stopped processes and lock owners were checked; orphan locks were released; Terraform's failed-apply state was pushed without forcing lineage/serial overrides; accepted AWS resources were imported rather than recreated. A refreshable credential-process bridge now uses the underlying AWS CLI browser session. No staging resources were deleted or replaced during reconciliation.

Terraform state/plan files contain credentials and are ignored by Git. The failed-apply state file was restricted to the Windows owner and SYSTEM. Never print the credential-process helper's stdout: it is a private SDK protocol. The approved infrastructure can accrue charges while code qualification continues.

## Production promotion

Do not promote while any gate above fails or lacks evidence. Production needs separately approved costs and credentials, verified DNS/HTTPS, confirmed operational/backup ownership, alert delivery, legal approval, and passing restore/rollback/load/security evidence. Promote the exact staged images. Record production smoke results and observe the seven-day launch before reconsidering a 9/10 rating. Availability remains a target until measured.
