terraform {
  required_version = ">= 1.10"
  required_providers {
    aws    = { source = "hashicorp/aws", version = ">= 6.0, < 7.0" }
    random = { source = "hashicorp/random", version = "~> 3.7" }
  }
  backend "s3" {
    bucket       = "talktobot-staging-tfstate-510439383733"
    key          = "staging/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["510439383733"]
  default_tags {
    tags = { Project = "TalkToBot", Environment = "staging", ManagedBy = "Terraform" }
  }
}

data "aws_availability_zones" "available" { state = "available" }
data "aws_caller_identity" "current" {}
locals {
  name = "talktobot-staging"
  azs  = slice(data.aws_availability_zones.available.names, 0, 3)
}

resource "aws_vpc" "staging" {
  cidr_block           = "10.80.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = local.name }
}
resource "aws_internet_gateway" "staging" { vpc_id = aws_vpc.staging.id }
resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.staging.id
  cidr_block              = cidrsubnet(aws_vpc.staging.cidr_block, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false
  tags                    = { "kubernetes.io/role/elb" = "1" }
}
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.staging.id
  cidr_block        = cidrsubnet(aws_vpc.staging.cidr_block, 8, count.index + 10)
  availability_zone = local.azs[count.index]
  tags              = { "kubernetes.io/role/internal-elb" = "1" }
}
resource "aws_eip" "nat" { domain = "vpc" }
resource "aws_nat_gateway" "staging" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.staging]
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.staging.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.staging.id
  }
}
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.staging.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.staging.id
  }
}
resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.staging.id
  service_name      = "com.amazonaws.ap-south-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
}

resource "aws_iam_role" "cluster" {
  name               = "${local.name}-cluster"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "eks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}
resource "aws_eks_cluster" "staging" {
  name                      = local.name
  version                   = "1.36"
  role_arn                  = aws_iam_role.cluster.arn
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }
  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = false
  }
  depends_on = [aws_iam_role_policy_attachment.cluster]
  encryption_config {
    provider { key_arn = aws_kms_key.staging.arn }
    resources = ["secrets"]
  }
}
resource "aws_iam_role" "nodes" {
  name               = "${local.name}-nodes"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "nodes" {
  for_each   = toset(["AmazonEKSWorkerNodePolicy", "AmazonEC2ContainerRegistryPullOnly", "AmazonEKS_CNI_Policy", "AmazonSSMManagedInstanceCore"])
  role       = aws_iam_role.nodes.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}
resource "aws_launch_template" "nodes" {
  name_prefix = "${local.name}-"
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 80
      volume_type = "gp3"
      encrypted   = true
    }
  }
}
resource "aws_eks_node_group" "staging" {
  cluster_name    = aws_eks_cluster.staging.name
  node_group_name = "application"
  node_role_arn   = aws_iam_role.nodes.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = ["m6i.xlarge"]
  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 2
  }
  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }
  update_config { max_unavailable = 1 }
  depends_on = [aws_iam_role_policy_attachment.nodes, aws_route_table_association.private]
}

resource "aws_security_group" "data" {
  name   = "${local.name}-data"
  vpc_id = aws_vpc.staging.id
}
resource "aws_vpc_security_group_ingress_rule" "data" {
  for_each                     = { postgres = 5432, redis = 6379, rabbitmq = 5671, kafka = 9096 }
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = aws_eks_cluster.staging.vpc_config[0].cluster_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = each.value
  to_port                      = each.value
}
resource "aws_vpc_security_group_ingress_rule" "broker_internal" {
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = aws_security_group.data.id
  ip_protocol                  = "-1"
}
resource "aws_vpc_security_group_egress_rule" "broker_internal" {
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = aws_security_group.data.id
  ip_protocol                  = "-1"
}
resource "aws_db_subnet_group" "staging" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_db_instance" "staging" {
  identifier                      = local.name
  engine                          = "postgres"
  engine_version                  = "16.15"
  instance_class                  = "db.t4g.medium"
  allocated_storage               = 50
  max_allocated_storage           = 100
  storage_type                    = "gp3"
  storage_encrypted               = true
  db_name                         = "talktobot"
  username                        = "talktobot_migrator"
  manage_master_user_password     = true
  db_subnet_group_name            = aws_db_subnet_group.staging.name
  vpc_security_group_ids          = [aws_security_group.data.id]
  publicly_accessible             = false
  multi_az                        = false
  backup_retention_period         = 35
  backup_window                   = "19:00-20:00"
  copy_tags_to_snapshot           = true
  deletion_protection             = true
  skip_final_snapshot             = false
  final_snapshot_identifier       = "talktobot-staging-final"
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
}
resource "aws_elasticache_subnet_group" "staging" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_elasticache_replication_group" "staging" {
  replication_group_id       = local.name
  description                = "Isolated staging authentication and cache"
  engine                     = "redis"
  node_type                  = "cache.t4g.small"
  num_cache_clusters         = 1
  subnet_group_name          = aws_elasticache_subnet_group.staging.name
  security_group_ids         = [aws_security_group.data.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis.result
  snapshot_retention_limit   = 7
}
resource "random_password" "redis" {
  length  = 40
  special = false
}
resource "random_password" "rabbitmq" {
  length  = 40
  special = false
}
resource "aws_mq_broker" "staging" {
  broker_name                = local.name
  engine_type                = "RabbitMQ"
  engine_version             = "4.3"
  host_instance_type         = "mq.m7g.medium"
  deployment_mode            = "SINGLE_INSTANCE"
  auto_minor_version_upgrade = true
  publicly_accessible        = false
  subnet_ids                 = [aws_subnet.private[0].id]
  security_groups            = [aws_security_group.data.id]
  user {
    username = "talktobot"
    password = random_password.rabbitmq.result
  }
  logs { general = true }
}

resource "aws_s3_bucket" "media" {
  bucket        = "talktobot-staging-media-510439383733"
  force_destroy = false
}
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.staging.arn
    }
  }
}
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  cors_rule {
    allowed_origins = ["https://staging.talktobot.com", "https://app.staging.talktobot.com", "https://api.staging.talktobot.com"]
    allowed_methods = ["GET", "HEAD", "POST", "PUT"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "x-amz-version-id"]
    max_age_seconds = 600
  }
}
resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.media.arn, "${aws_s3_bucket.media.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }, { Effect = "Deny", Principal = "*", Action = "s3:DeleteObjectVersion", Resource = "${aws_s3_bucket.media.arn}/*" }] })
}

output "cluster_name" { value = aws_eks_cluster.staging.name }
output "database_endpoint" { value = aws_db_instance.staging.address }
output "database_master_secret_arn" { value = aws_db_instance.staging.master_user_secret[0].secret_arn }
output "redis_endpoint" { value = aws_elasticache_replication_group.staging.primary_endpoint_address }
output "rabbitmq_endpoint" { value = aws_mq_broker.staging.instances[0].endpoints[0] }
output "media_bucket" { value = aws_s3_bucket.media.id }
