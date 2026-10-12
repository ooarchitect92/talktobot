# Provider values are written directly to Secrets Manager, never Terraform state.
resource "aws_secretsmanager_secret" "providers" {
  name                    = "talktobot/staging/providers"
  kms_key_id              = aws_kms_key.staging.arn
  recovery_window_in_days = 30
}
