resource "aws_kms_key" "staging" {
  description             = "TalkToBot staging secrets and Kafka"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}
resource "random_password" "kafka" {
  length  = 40
  special = false
}
resource "aws_secretsmanager_secret" "kafka" {
  name                    = "AmazonMSK_talktobot_staging"
  kms_key_id              = aws_kms_key.staging.arn
  recovery_window_in_days = 30
}
resource "aws_secretsmanager_secret_version" "kafka" {
  secret_id     = aws_secretsmanager_secret.kafka.id
  secret_string = jsonencode({ username = "talktobot", password = random_password.kafka.result })
}
resource "aws_msk_cluster" "staging" {
  cluster_name           = local.name
  kafka_version          = "3.9.x"
  number_of_broker_nodes = 3
  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = aws_subnet.private[*].id
    security_groups = [aws_security_group.data.id]
    storage_info {
      ebs_storage_info { volume_size = 20 }
    }
  }
  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.staging.arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }
  client_authentication {
    sasl { scram = true }
    unauthenticated = false
  }
}
resource "aws_msk_scram_secret_association" "staging" {
  cluster_arn     = aws_msk_cluster.staging.arn
  secret_arn_list = [aws_secretsmanager_secret.kafka.arn]
  depends_on      = [aws_secretsmanager_secret_version.kafka]
}

resource "random_password" "application" {
  for_each = toset(["jwt", "mfa", "crm", "website_proxy", "database_app", "database_service"])
  length   = 48
  special  = false
}
resource "aws_secretsmanager_secret" "application" {
  name                    = "talktobot/staging/application"
  kms_key_id              = aws_kms_key.staging.arn
  recovery_window_in_days = 30
}
resource "aws_secretsmanager_secret_version" "application" {
  secret_id = aws_secretsmanager_secret.application.id
  secret_string = jsonencode({
    JWT_SECRET                    = random_password.application["jwt"].result
    MFA_ENCRYPTION_KEY            = random_password.application["mfa"].result
    CRM_CREDENTIAL_ENCRYPTION_KEY = random_password.application["crm"].result
    WEBSITE_PROXY_SECRET          = random_password.application["website_proxy"].result
    DATABASE_APP_PASSWORD         = random_password.application["database_app"].result
    DATABASE_URL                  = "postgresql+asyncpg://talktobot_runtime:${random_password.application["database_app"].result}@${aws_db_instance.staging.address}:5432/talktobot?ssl=verify-full"
    DATABASE_SERVICE_PASSWORD     = random_password.application["database_service"].result
    WORKER_DATABASE_URL           = "postgresql+asyncpg://northstar_service:${random_password.application["database_service"].result}@${aws_db_instance.staging.address}:5432/talktobot?ssl=verify-full"
    RABBITMQ_URL                  = "${replace(aws_mq_broker.staging.instances[0].endpoints[0], "amqps://", "amqps://talktobot:${urlencode(random_password.rabbitmq.result)}@")}/"
    KAFKA_SASL_USERNAME           = "talktobot"
    KAFKA_SASL_PASSWORD           = random_password.kafka.result
    REDIS_AUTH_TOKEN              = random_password.redis.result
    REDIS_URL                     = "rediss://:${random_password.redis.result}@${aws_elasticache_replication_group.staging.primary_endpoint_address}:6379/0"
    RABBITMQ_PASSWORD             = random_password.rabbitmq.result
  })
}

resource "aws_iam_role" "workload" {
  name = "${local.name}-workload"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }, Action = ["sts:AssumeRole", "sts:TagSession"]
    Condition = { StringEquals = {
      "aws:RequestTag/eks-cluster-arn"            = aws_eks_cluster.staging.arn
      "aws:RequestTag/kubernetes-namespace"       = "northstar"
      "aws:RequestTag/kubernetes-service-account" = "northstar-workload"
    } }
  }] })
}
resource "aws_iam_role_policy" "workload" {
  role = aws_iam_role.workload.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.media.arn },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.media.arn}/*" }
    , { Effect = "Allow", Action = ["kms:Decrypt", "kms:GenerateDataKey"], Resource = aws_kms_key.staging.arn, Condition = { StringEquals = { "kms:ViaService" = "s3.ap-south-1.amazonaws.com" }, StringLike = { "kms:EncryptionContext:aws:s3:arn" = [aws_s3_bucket.media.arn, "${aws_s3_bucket.media.arn}/*"] } } }
  ] })
}
resource "aws_eks_addon" "pod_identity" {
  cluster_name = aws_eks_cluster.staging.name
  addon_name   = "eks-pod-identity-agent"
  depends_on   = [aws_eks_node_group.staging]
}
resource "aws_eks_pod_identity_association" "application" {
  cluster_name    = aws_eks_cluster.staging.name
  namespace       = "northstar"
  service_account = "northstar-workload"
  role_arn        = aws_iam_role.workload.arn
  depends_on      = [aws_eks_addon.pod_identity]
}

resource "aws_sns_topic" "operations" {
  name              = "talktobot-staging-operations"
  kms_master_key_id = aws_kms_key.alerts.arn
}
resource "aws_kms_key" "alerts" {
  description             = "TalkToBot staging operational alerts"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Principal = { AWS = "arn:aws:iam::510439383733:root" }, Action = "kms:*", Resource = "*" },
    { Effect = "Allow", Principal = { Service = "cloudwatch.amazonaws.com" }, Action = ["kms:Decrypt", "kms:GenerateDataKey*"], Resource = "*", Condition = { StringEquals = { "aws:SourceAccount" = "510439383733" }, ArnLike = { "aws:SourceArn" = "arn:aws:cloudwatch:ap-south-1:510439383733:alarm:talktobot-staging-*" } } }
  ] })
}
resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "talktobot-staging-database-storage"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.staging.identifier }
  comparison_operator = "LessThanThreshold"
  threshold           = 10737418240
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.operations.arn]
  treat_missing_data  = "breaching"
}
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "talktobot-staging-database-cpu"
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.staging.identifier }
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  alarm_actions       = [aws_sns_topic.operations.arn]
  treat_missing_data  = "breaching"
}
output "kafka_bootstrap_scram" { value = aws_msk_cluster.staging.bootstrap_brokers_sasl_scram }
output "application_secret_arn" { value = aws_secretsmanager_secret.application.arn }
output "operations_topic_arn" { value = aws_sns_topic.operations.arn }
