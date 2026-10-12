# Private AWS images remain pullable after a short-lived GitHub token expires.
resource "aws_ecr_repository" "application" {
  for_each             = toset(["api", "web", "website"])
  name                 = "talktobot-staging/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.staging.arn
  }
}

resource "aws_ecr_lifecycle_policy" "application" {
  for_each   = aws_ecr_repository.application
  repository = each.value.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Retain thirty immutable release tags for rollback"
    selection    = { tagStatus = "tagged", tagPrefixList = ["sha-"], countType = "imageCountMoreThan", countNumber = 30 }
    action       = { type = "expire" }
  }] })
}

resource "aws_iam_role" "github_image_publish" {
  name = "talktobot-staging-image-publish"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow"
    Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
    Action    = "sts:AssumeRoleWithWebIdentity"
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
      "token.actions.githubusercontent.com:sub" = "repo:ooarchitect92@274523797/talktobot@1415168926:environment:staging"
    } }
  }] })
}

resource "aws_iam_role_policy" "github_image_publish" {
  role = aws_iam_role.github_image_publish.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:DescribeImages"], Resource = [for repo in aws_ecr_repository.application : repo.arn] }
  ] })
}
