# The confirmed domain is talktobot.com. Retain the old, undelegated .io zone
# until cleanup is reviewed; changing the domain must not destroy existing DNS.
resource "aws_route53_zone" "staging_com" {
  name = "staging.talktobot.com"
}

resource "aws_acm_certificate" "staging_com" {
  domain_name               = "staging.talktobot.com"
  subject_alternative_names = ["*.staging.talktobot.com"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
}

# The apex and wildcard share one ACM validation record. Manage it once.
resource "aws_route53_record" "certificate_com" {
  zone_id = aws_route53_zone.staging_com.zone_id
  name = one([
    for option in aws_acm_certificate.staging_com.domain_validation_options : option.resource_record_name
    if option.domain_name == "staging.talktobot.com"
  ])
  type = "CNAME"
  records = [one([
    for option in aws_acm_certificate.staging_com.domain_validation_options : option.resource_record_value
    if option.domain_name == "staging.talktobot.com"
  ])]
  ttl = 300
}

output "staging_com_nameservers" { value = aws_route53_zone.staging_com.name_servers }
output "staging_com_certificate_arn" { value = aws_acm_certificate.staging_com.arn }
