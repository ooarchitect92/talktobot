"""Create the approved staging Terraform state bucket without printing credentials."""
from __future__ import annotations

import json
import subprocess

import boto3
from botocore.exceptions import ClientError

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
ACCOUNT = "510439383733"
BUCKET = "talktobot-staging-tfstate-510439383733"


def main() -> None:
    identity = json.loads(subprocess.check_output([AWS, "sts", "get-caller-identity", "--profile", "northstar-iam", "--region", "ap-south-1", "--output", "json", "--no-cli-pager"]))
    if identity["Account"] != ACCOUNT:
        raise RuntimeError("Unexpected AWS account")
    credentials = json.loads(subprocess.check_output([AWS, "configure", "export-credentials", "--profile", "northstar-iam", "--format", "process"]))
    s3 = boto3.client("s3", region_name="ap-south-1", aws_access_key_id=credentials["AccessKeyId"], aws_secret_access_key=credentials["SecretAccessKey"], aws_session_token=credentials["SessionToken"])
    try:
        s3.head_bucket(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT)
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
            raise
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    s3.put_public_access_block(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT, PublicAccessBlockConfiguration={"BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    s3.put_bucket_versioning(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT, VersioningConfiguration={"Status": "Enabled"})
    s3.put_bucket_encryption(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT, ServerSideEncryptionConfiguration={"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
    s3.put_bucket_tagging(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT, Tagging={"TagSet": [{"Key": "Project", "Value": "TalkToBot"}, {"Key": "Environment", "Value": "staging"}, {"Key": "ManagedBy", "Value": "bootstrap-staging-state.py"}]})
    s3.put_bucket_policy(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT, Policy=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Principal": "*", "Action": "s3:*", "Resource": [f"arn:aws:s3:::{BUCKET}", f"arn:aws:s3:::{BUCKET}/*"], "Condition": {"Bool": {"aws:SecureTransport": "false"}}}, {"Effect": "Deny", "Principal": "*", "Action": "s3:DeleteObjectVersion", "Resource": f"arn:aws:s3:::{BUCKET}/*"}]}))
    print(json.dumps({"account": ACCOUNT, "region": "ap-south-1", "stateBucket": BUCKET, "versioning": True, "publicAccessBlocked": True}))


if __name__ == "__main__":
    main()
