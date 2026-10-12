# Standard controller permissions pinned to the v3.6.0 upstream policy.
# Credentials are bound to this staging cluster and controller service account.
resource "aws_iam_role" "load_balancer_controller" {
  name = "talktobot-staging-load-balancer-controller"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-arn"            = aws_eks_cluster.staging.arn
          "aws:RequestTag/kubernetes-namespace"       = "kube-system"
          "aws:RequestTag/kubernetes-service-account" = "aws-load-balancer-controller"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "load_balancer_controller" {
  role   = aws_iam_role.load_balancer_controller.id
  policy = file("${path.module}/load-balancer-controller-policy.json")
}

resource "aws_eks_pod_identity_association" "load_balancer_controller" {
  cluster_name    = aws_eks_cluster.staging.name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.load_balancer_controller.arn
  depends_on      = [aws_eks_addon.pod_identity, aws_iam_role_policy.load_balancer_controller]
}
