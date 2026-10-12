param(
    [ValidateSet('northstar-iam', 'northstar-dev')][string]$Profile = 'northstar-iam',
    [ValidateRange(1024, 65535)][int]$LocalPort = 9443
)
$ErrorActionPreference = 'Stop'
$awsExecutable = 'C:/Program Files/Amazon/AWSCLIV2/aws.exe'
$pluginDirectory = 'C:/Program Files/Amazon/SessionManagerPlugin/bin'
if (!(Test-Path "$pluginDirectory/session-manager-plugin.exe")) { throw 'AWS Session Manager plugin is required.' }
$identity = & $awsExecutable sts get-caller-identity --profile $Profile --region ap-south-1 --output json --no-cli-pager | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $identity.Account -ne '510439383733') { throw 'Expected staging account is not authenticated.' }
if (Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue) { throw 'Requested local port is already in use.' }
$cluster = & $awsExecutable eks describe-cluster --name talktobot-staging --profile $Profile --region ap-south-1 --output json --no-cli-pager | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $cluster.cluster.status -ne 'ACTIVE' -or $cluster.cluster.resourcesVpcConfig.endpointPublicAccess) { throw 'Expected active private staging cluster.' }
$nodes = & $awsExecutable ec2 describe-instances --filters 'Name=tag:eks:cluster-name,Values=talktobot-staging' 'Name=instance-state-name,Values=running' --profile $Profile --region ap-south-1 --output json --no-cli-pager | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify staging nodes.' }
$nodeIds = @($nodes.Reservations | ForEach-Object { $_.Instances } | ForEach-Object { $_.InstanceId })
$managed = & $awsExecutable ssm describe-instance-information --profile $Profile --region ap-south-1 --output json --no-cli-pager | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify SSM availability.' }
$node = $managed.InstanceInformationList | Where-Object { $_.InstanceId -in $nodeIds -and $_.PingStatus -eq 'Online' } | Select-Object -First 1
if (!$node) { throw 'No online SSM-managed staging node.' }
$directory = Join-Path (Split-Path -Parent $PSScriptRoot) 'reports/readiness'
$remoteHost = ([uri]$cluster.cluster.endpoint).Host
$parameters = Join-Path $directory 'staging-tunnel-parameters.json'
@{host=@($remoteHost);portNumber=@('443');localPortNumber=@([string]$LocalPort)} | ConvertTo-Json -Compress | Set-Content -LiteralPath $parameters -Encoding ascii
$configPath = Join-Path $directory 'staging.kubeconfig'
$kubeconfig = @{
    apiVersion='v1';kind='Config';'current-context'='talktobot-staging-private';
    clusters=@(@{name='staging';cluster=@{server="https://127.0.0.1:$LocalPort";'tls-server-name'=$remoteHost;'certificate-authority-data'=$cluster.cluster.certificateAuthority.data}});
    contexts=@(@{name='talktobot-staging-private';context=@{cluster='staging';user='staging-operator';namespace='northstar'}});
    users=@(@{name='staging-operator';user=@{exec=@{apiVersion='client.authentication.k8s.io/v1beta1';command=$awsExecutable;args=@('eks','get-token','--cluster-name','talktobot-staging','--profile',$Profile,'--region','ap-south-1');interactiveMode='Never'}}})
}
$kubeconfig | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $configPath -Encoding ascii
$previousPath = $env:PATH
try {
    $env:PATH = "$pluginDirectory;$previousPath"
    $arguments = @('ssm','start-session','--target',$node.InstanceId,'--document-name','AWS-StartPortForwardingSessionToRemoteHost','--parameters',"file://$($parameters.Replace('\','/'))",'--profile',$Profile,'--region','ap-south-1','--no-cli-pager')
    $process = Start-Process -FilePath $awsExecutable -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $directory 'staging-tunnel.log') -RedirectStandardError (Join-Path $directory 'staging-tunnel-errors.log')
} finally { $env:PATH = $previousPath }
@{processId=$process.Id;nodeId=$node.InstanceId;localPort=$LocalPort;kubeconfig=$configPath} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $directory 'staging-tunnel-receipt.json') -Encoding ascii
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if (Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue) {
        Write-Output "Private staging tunnel ready. Use kubectl --kubeconfig $configPath."
        exit 0
    }
    $process.Refresh()
    if ($process.HasExited) { throw 'SSM tunnel exited; inspect the private tunnel logs.' }
    Start-Sleep -Seconds 1
}
throw 'Tunnel is still starting; inspect the private tunnel receipt and logs.'
