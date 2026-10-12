"""Initialize only the local Compose S3 server, using the application's SDK."""
import os

import boto3
from botocore.exceptions import ClientError


def initialize(client, bucket):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        client.create_bucket(Bucket=bucket)
    client.delete_bucket_policy(Bucket=bucket)
    client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    try:
        rules = client.get_bucket_lifecycle_configuration(Bucket=bucket).get("Rules", [])
    except ClientError as error:
        if error.response["Error"]["Code"] != "NoSuchLifecycleConfiguration":
            raise
        rules = []
    if not any(rule.get("Filter", {}).get("Prefix", rule.get("Prefix")) == "staging/" for rule in rules):
        rules.append({
            "ID": "talktobot-local-staging-cleanup", "Status": "Enabled", "Filter": {"Prefix": "staging/"},
            "Expiration": {"Days": 1}, "NoncurrentVersionExpiration": {"NoncurrentDays": 1},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
        })
        client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": rules})


if __name__ == "__main__":
    local = boto3.client("s3", endpoint_url="http://minio:9000", region_name="us-east-1",
                         aws_access_key_id=os.environ["MINIO_ROOT_USER"],
                         aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"])
    initialize(local, os.environ["S3_BUCKET"])
    print("Local private, versioned object storage initialized.")
