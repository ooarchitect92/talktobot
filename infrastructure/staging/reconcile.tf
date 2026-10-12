# The first Windows provisioning process stopped after AWS accepted these creates,
# before Terraform could persist their completed state. Import instead of duplicating.
import {
  to = aws_eks_cluster.staging
  id = "talktobot-staging"
}
import {
  to = aws_db_instance.staging
  id = "talktobot-staging"
}
import {
  to = aws_msk_cluster.staging
  id = "arn:aws:kafka:ap-south-1:510439383733:cluster/talktobot-staging/4832b0d2-18c1-495a-9121-fe9f8b0a7dcc-4"
}
