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
        "token.actions.githubusercontent.com:sub" = "repo:ooarchitect92/talktobot:environment:staging"
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
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.application.arn },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = aws_kms_key.staging.arn,
        Condition = { StringEquals = {
          "kms:ViaService"                  = "secretsmanager.ap-south-1.amazonaws.com"
          "kms:EncryptionContext:SecretARN" = aws_secretsmanager_secret.application.arn
      } } },
      { Effect = "Allow", Action = ["elasticache:DescribeReplicationGroups"], Resource = "*" }
    ]
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
