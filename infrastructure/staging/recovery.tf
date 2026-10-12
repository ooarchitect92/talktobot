resource "aws_iam_role" "recovery" {
  name               = "${local.name}-recovery"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { AWS = "arn:aws:iam::510439383733:user/@ni" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "recovery" {
  role = aws_iam_role.recovery.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["rds:DescribeDBInstances", "rds:DescribeDBSnapshots", "rds:DescribeDBSubnetGroups"], Resource = "*" },
    { Effect = "Allow", Action = ["rds:RestoreDBInstanceToPointInTime", "rds:RestoreDBInstanceFromDBSnapshot", "rds:AddTagsToResource"], Resource = [aws_db_instance.staging.arn, aws_db_subnet_group.staging.arn, "arn:aws:rds:ap-south-1:510439383733:db:talktobot-staging-restore-*", "arn:aws:rds:ap-south-1:510439383733:snapshot:talktobot-staging-*"] },
    { Effect = "Allow", Action = ["s3:ListBucket", "s3:ListBucketVersions"], Resource = aws_s3_bucket.media.arn },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"], Resource = "${aws_s3_bucket.media.arn}/*" },
    { Effect = "Allow", Action = ["kms:Decrypt"], Resource = aws_kms_key.staging.arn, Condition = { StringEquals = { "kms:ViaService" = "s3.ap-south-1.amazonaws.com" } } }
  ] })
}
output "recovery_role_arn" { value = aws_iam_role.recovery.arn }

