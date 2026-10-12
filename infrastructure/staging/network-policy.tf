# Existing self-managed CNI had its policy agent disabled. Adopt the compatible
# managed add-on so Kubernetes NetworkPolicy manifests actually enforce rules.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.staging.name
  addon_name                  = "vpc-cni"
  addon_version               = "v1.22.4-eksbuild.3"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  configuration_values        = jsonencode({ enableNetworkPolicy = "true" })
}
