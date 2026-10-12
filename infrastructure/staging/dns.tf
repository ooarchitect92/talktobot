# Delegate only staging.talktobot.io from GoDaddy; leave root domain ownership alone.
resource "aws_route53_zone" "staging" { name = "staging.talktobot.io" }
resource "aws_acm_certificate" "staging" {
  domain_name               = "staging.talktobot.io"
  subject_alternative_names = ["*.staging.talktobot.io"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
}
resource "aws_route53_record" "certificate" {
  for_each        = { for option in aws_acm_certificate.staging.domain_validation_options : option.domain_name => option }
  zone_id         = aws_route53_zone.staging.zone_id
  name            = each.value.resource_record_name
  type            = each.value.resource_record_type
  records         = [each.value.resource_record_value]
  ttl             = 300
  allow_overwrite = true
}
output "staging_nameservers" { value = aws_route53_zone.staging.name_servers }
output "staging_certificate_arn" { value = aws_acm_certificate.staging.arn }
