resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_staging_deploy" {
  name = "talktobot-staging-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = "repo:ooarchitect92@274523797/talktobot@1415168926:environment:staging"
      } }
    }]
  })
}

resource "aws_iam_role_policy" "github_staging_deploy" {
  role = aws_iam_role.github_staging_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["eks:DescribeCluster"], Resource = aws_eks_cluster.staging.arn },
      { Effect = "Allow", Action = ["rds:DescribeDBInstances"], Resource = aws_db_instance.staging.arn },
      { Effect = "Allow", Action = ["ecr:DescribeImages"], Resource = [for repo in aws_ecr_repository.application : repo.arn] },
      { Effect = "Allow", Action = ["elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeRules"], Resource = "*" },
      { Effect = "Allow", Action = ["route53:ChangeResourceRecordSets"], Resource = aws_route53_zone.staging_com.arn,
        Condition = { "ForAllValues:StringEquals" = {
          "route53:ChangeResourceRecordSetsNormalizedRecordNames" = ["staging.talktobot.com", "app.staging.talktobot.com", "api.staging.talktobot.com"]
          "route53:ChangeResourceRecordSetsRecordTypes"           = ["A"]
          "route53:ChangeResourceRecordSetsActions"               = ["UPSERT"]
      } } },
      { Effect = "Allow", Action = ["route53:GetChange"], Resource = "arn:aws:route53:::change/*" },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [aws_secretsmanager_secret.application.arn, aws_secretsmanager_secret.providers.arn, aws_db_instance.staging.master_user_secret[0].secret_arn] },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = aws_kms_key.staging.arn,
        Condition = { StringEquals = {
          "kms:ViaService"                  = "secretsmanager.ap-south-1.amazonaws.com"
          "kms:EncryptionContext:SecretARN" = [aws_secretsmanager_secret.application.arn, aws_secretsmanager_secret.providers.arn]
      } } },
      { Effect = "Allow", Action = ["elasticache:DescribeReplicationGroups"], Resource = "*" }
      , { Effect = "Allow", Action = ["ec2:DescribeInstances", "ssm:DescribeInstanceInformation"], Resource = "*",
      Condition = { StringEquals = { "aws:RequestedRegion" = "ap-south-1" } } }
      , { Effect = "Allow", Action = ["ssm:StartSession"], Resource = aws_ssm_document.staging_eks_tunnel.arn }
      , { Effect = "Allow", Action = ["ssm:StartSession"], Resource = "arn:aws:ec2:ap-south-1:510439383733:instance/*",
      Condition = { StringEquals = { "ssm:resourceTag/eks:cluster-name" = "talktobot-staging" } } }
      , { Effect = "Allow", Action = ["ssmmessages:OpenDataChannel"], Resource = "arn:aws:ssm:ap-south-1:510439383733:session/talktobot-*" }
      , { Effect = "Allow", Action = ["ssm:TerminateSession"], Resource = "arn:aws:ssm:ap-south-1:510439383733:session/talktobot-*",
      Condition = { StringEquals = { "ssm:resourceTag/aws:ssmmessages:session-id" = "$${aws:userid}" } } }
    ]
  })
}

# No shell, SSH, or caller-selected remote host: this document only connects to
# this cluster's private Kubernetes HTTPS endpoint.
resource "aws_ssm_document" "staging_eks_tunnel" {
  name            = "talktobot-staging-eks-tunnel"
  document_type   = "Session"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Private staging Kubernetes HTTPS tunnel"
    sessionType   = "Port"
    parameters = { localPortNumber = {
      type = "String", default = "9443", allowedPattern = "^9443$"
    } }
    properties = {
      host            = trimprefix(aws_eks_cluster.staging.endpoint, "https://")
      portNumber      = "443"
      localPortNumber = "{{ localPortNumber }}"
    }
  })
}

resource "aws_eks_access_entry" "github_staging_deploy" {
  cluster_name  = aws_eks_cluster.staging.name
  principal_arn = aws_iam_role.github_staging_deploy.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "github_staging_deploy" {
  cluster_name  = aws_eks_cluster.staging.name
  principal_arn = aws_iam_role.github_staging_deploy.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
  access_scope {
    type       = "namespace"
    namespaces = ["northstar"]
  }
  depends_on = [aws_eks_access_entry.github_staging_deploy]
}

output "github_staging_deploy_role_arn" {
  value = aws_iam_role.github_staging_deploy.arn
}
