"""Read-only AWS deployment inventory; never reads secret values or credentials."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--profile', default='northstar-iam')
parser.add_argument('--output', default='docs/operations/aws-inventory-2026-10-12.json')
args = parser.parse_args()
aws = shutil.which('aws') or 'C:/Program Files/Amazon/AWSCLIV2/aws.exe'


def query(region: str, service: str, action: str, expression: str):
    command = [aws, service, action, '--profile', args.profile, '--region', region,
               '--query', expression, '--output', 'json', '--no-cli-pager',
               '--cli-connect-timeout', '5', '--cli-read-timeout', '15']
    result = subprocess.run(command, capture_output=True, text=True, timeout=35)
    if result.returncode:
        return {'error': result.stderr.strip()[:500]}
    return json.loads(result.stdout)


identity = query('ap-south-1', 'sts', 'get-caller-identity', '{Account:Account,Arn:Arn}')
if 'error' in identity:
    raise SystemExit(identity['error'])
regions = query('ap-south-1', 'ec2', 'describe-regions', 'Regions[].RegionName')
if isinstance(regions, dict):
    raise SystemExit(regions['error'])
checks = [
    ('ec2', 'describe-instances', 'Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,State:State.Name,Vpc:VpcId}'),
    ('eks', 'list-clusters', 'clusters'),
    ('ecs', 'list-clusters', 'clusterArns'),
    ('rds', 'describe-db-instances', 'DBInstances[].{Id:DBInstanceIdentifier,Engine:Engine,BackupDays:BackupRetentionPeriod,MultiAZ:MultiAZ,Public:PubliclyAccessible}'),
    ('elasticache', 'describe-cache-clusters', 'CacheClusters[].{Id:CacheClusterId,Engine:Engine}'),
    ('mq', 'list-brokers', 'BrokerSummaries[].{Id:BrokerId,Name:BrokerName}'),
    ('kafka', 'list-clusters-v2', 'ClusterInfoList[].{Arn:ClusterArn,Name:ClusterName}'),
    ('lambda', 'list-functions', 'Functions[].{Name:FunctionName,Runtime:Runtime}'),
    ('lightsail', 'get-instances', 'instances[].{Name:name,State:state.name}'),
    ('acm', 'list-certificates', 'CertificateSummaryList[].{Domain:DomainName,Status:Status}'),
]
report = {'captured_at': datetime.now(UTC).isoformat(), 'identity': identity, 'regions': {}, 'global': {}}


def run(region, check):
    service, action, expression = check
    try:
        return region, service, query(region, service, action, expression)
    except (subprocess.TimeoutExpired, ValueError) as exc:
        return region, service, {'error': type(exc).__name__}


with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(run, region, check) for region in regions for check in checks]
    for future in as_completed(futures):
        region, service, value = future.result()
        report['regions'].setdefault(region, {})[service] = value
        if value:
            print(json.dumps({'region': region, 'service': service, 'result': value}), flush=True)
for service, action, expression in [
    ('s3api', 'list-buckets', 'Buckets[].Name'),
    ('route53', 'list-hosted-zones', 'HostedZones[].{Id:Id,Name:Name}'),
    ('cloudfront', 'list-distributions', 'DistributionList.Items[].{Id:Id,Domain:DomainName,Enabled:Enabled}'),
]:
    report['global'][service] = query('us-east-1', service, action, expression)
target = Path(args.output)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Inventory saved: {target}', flush=True)
