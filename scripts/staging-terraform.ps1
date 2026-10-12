param(
    [Parameter(Mandatory)][ValidateSet('init', 'validate', 'plan', 'apply', 'output', 'state-list', 'unlock', 'recover-state')][string]$Action,
    [ValidateSet('northstar-iam', 'northstar-dev')][string]$Profile = 'northstar-iam',
    [ValidatePattern('^[0-9a-f-]{36}$')][string]$UnlockId,
    [ValidateSet('aws_s3_bucket_cors_configuration.media', 'aws_ssm_document.staging_eks_tunnel', 'aws_iam_role.workload', 'aws_ecr_repository.application', 'aws_ecr_lifecycle_policy.application', 'aws_iam_role.github_image_publish', 'aws_iam_role_policy.github_image_publish', 'aws_secretsmanager_secret_version.application', 'aws_secretsmanager_secret.providers', 'aws_iam_role_policy.github_staging_deploy', 'aws_eks_addon.vpc_cni', 'aws_iam_role.load_balancer_controller', 'aws_iam_role_policy.load_balancer_controller', 'aws_eks_pod_identity_association.load_balancer_controller', 'aws_eks_node_group.staging', 'aws_mq_broker.staging', 'aws_route53_record.certificate', 'aws_route53_zone.staging_com', 'aws_acm_certificate.staging_com', 'aws_route53_record.certificate_com', 'aws_eks_pod_identity_association.application', 'aws_cloudwatch_metric_alarm.database_storage', 'aws_cloudwatch_metric_alarm.database_cpu', 'aws_s3_bucket_server_side_encryption_configuration.media')][string[]]$Targets
)
$ErrorActionPreference = 'Stop'
$awsExecutable = 'C:\Program Files\Amazon\AWSCLIV2\aws.exe'
$identity = & $awsExecutable sts get-caller-identity --profile $Profile --region ap-south-1 --output json --no-cli-pager | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $identity.Account -ne '510439383733') { throw 'Expected staging AWS account is not authenticated.' }
$originalConfig = $env:AWS_CONFIG_FILE
$originalProfile = $env:AWS_PROFILE
$repository = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repository 'backend/.venv/Scripts/python.exe'
$bridge = Join-Path $PSScriptRoot 'aws-credential-process.py'
if ($python -match '\s' -or $bridge -match '\s') { throw 'The local Windows credential bridge requires workspace paths without whitespace.' }
$python = $python.Replace('\', '/')
$bridge = $bridge.Replace('\', '/')
$bridgeConfig = Join-Path $repository 'reports/readiness/aws-terraform-config'
@"
[profile talktobot-terraform]
region = ap-south-1
credential_process = $python $bridge --profile $Profile
"@ | Set-Content -LiteralPath $bridgeConfig -Encoding ascii
$env:AWS_CONFIG_FILE = $bridgeConfig
$env:AWS_PROFILE = 'talktobot-terraform'
$env:AWS_REGION = 'ap-south-1'
try {
    $arguments = @('-chdir=infrastructure/staging', $Action, '-no-color')
    if ($Action -eq 'state-list') { $arguments = @('-chdir=infrastructure/staging', 'state', 'list') }
    if ($Action -eq 'recover-state') {
        if ((Get-Process terraform -ErrorAction SilentlyContinue) -or !(Test-Path (Join-Path $repository 'infrastructure/staging/errored.tfstate'))) { throw 'State recovery requires a stopped process and an existing failed-apply state file.' }
        $arguments = @('-chdir=infrastructure/staging', 'state', 'push', 'errored.tfstate')
    }
    if ($Action -eq 'unlock') {
        if (!$UnlockId -or (Get-Process terraform -ErrorAction SilentlyContinue)) { throw 'Only unlock an identified orphan after verifying there is no live Terraform process.' }
        $arguments = @('-chdir=infrastructure/staging', 'force-unlock', '-force', $UnlockId)
    }
    if ($Action -eq 'plan') { $arguments += @('-out=staging.tfplan', '-input=false') }
    if ($Action -eq 'plan') { foreach ($target in $Targets) { $arguments += "-target=$target" } }
    if ($Action -eq 'apply') { $arguments += @('-input=false', 'staging.tfplan') }
    # Windows PowerShell treats native stderr as ErrorRecord even for harmless
    # provider diagnostics. Judge Terraform by its exit status, not that stream.
    $ErrorActionPreference = 'Continue'
    & terraform @arguments 2>&1 | ForEach-Object { $_.ToString() }
    $terraformExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($terraformExit -ne 0) { throw "Terraform $Action failed with exit code $terraformExit." }
} finally {
    $env:AWS_CONFIG_FILE = $originalConfig
    $env:AWS_PROFILE = $originalProfile
}
