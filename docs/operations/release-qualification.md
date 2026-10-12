# TalkToBot release qualification

Status: **NOT QUALIFIED — public production launch blocked**.

Scope: public website, owner console, customer application, API and every enabled worker. Staging provisioning was approved on 2026-10-12 at the reviewed USD 800–1,000/month planning allowance. Production infrastructure and promotion remain unapproved.

## Evidence and limitations

| Gate | Evidence | Status |
|---|---|---|
| AWS identity | Account 510439383733, authenticated IAM user @ni | Verified |
| Staging infrastructure | Terraform main/security/recovery/DNS configuration; encrypted remote state; managed private data services; EKS API public access disabled | Provisioned |
| AWS Redis and OIDC | Private authenticated Redis TLS PING passed; 23 local Redis/config checks; staging-only OIDC role and namespace access configured | Basic connectivity verified; rollout and failover pending |
| Staging DNS / HTTPS | staging.talktobot.com delegation and validation records verified; Mumbai certificate 04cd6697-9b51-4eea-b573-eae1b047525b ISSUED | Certificate ready; load balancer attachment and application DNS pending |
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

## Runtime security and staging update, 2026-10-12

The prior Debian runtime scans are historical findings, not the current image result. The API now uses a digest-pinned Alpine 3.24 Python runtime and patched distribution LibreOffice/Tesseract packages. Playwright is a development-only QA dependency. `reports/readiness/api-alpine-security.json` records zero critical/high findings without ignoring unfixed vulnerabilities. Actual non-root, read-only DOCX-to-PDF rendering, OCR and native Python imports passed (`api-alpine-capabilities.log`). These checks precede later source edits and must be repeated for the published immutable images.

Restricted RDS TLS and hostname verification passed. The real database was migrated through `0082_service_audit_permissions`; API help/schema/migration writes and worker audit mutations are denied (`staging-postgres-boundaries.json`). Historical default grants unexpectedly retained help write access; the additive migration explicitly revokes it. Production startup no longer synchronizes global help through the API role. A separate migration job synchronized 118 help articles and 11 categories successfully; workers use their separate non-owner service identity.

The AWS load balancer controller is installed and pinned by digest, the VPC CNI network policy agent is enabled, and three encrypted immutable ECR repositories are provisioned. OIDC publishing preserves the scanned/attested GHCR digest in ECR. Application deployment uses a hosted GitHub runner and a restricted SSM port-forward document that fixes the private Kubernetes hostname/HTTPS port; no shell, SSH, public Kubernetes API or permanent runner is required. The deployment role cannot change this document.

Real SMTP authentication, NVIDIA chat and 2,048-dimensional embedding calls passed. Provider secrets are held in Secrets Manager and excluded from Terraform values and repository contents. Credentials disclosed in chat need rotation before public launch. No real email was sent by these connectivity checks. Billing and external delivery integrations remain disabled.

HTTPS ingress defaults to a deny-only CIDR. Controlled validation admits only the operator and staging NAT addresses. Public/customer exposure remains blocked until release and acceptance gates pass. There are no application workloads or load balancer DNS records deployed at this checkpoint. Recovery, rollback, one-hour 100-session load, 24-hour soak, alert delivery, backup ownership and seven-day launch evidence are still pending. No 9/10 rating or qualified release is claimed.


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
