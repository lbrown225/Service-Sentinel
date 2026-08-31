output "ecr_repository_url" {
  description = "URL used to tag and push Service Sentinel container images"
  value       = aws_ecr_repository.service_sentinel.repository_url
}

output "health_endpoint" {
  description = "Public URL for the production health endpoint"
  value       = "${aws_apigatewayv2_api.service_sentinel.api_endpoint}/health"
}

output "github_actions_deploy_role_arn" {
  description = "IAM role ARN assumed by the GitHub Actions deployment workflow"
  value       = aws_iam_role.github_actions_deploy.arn
}
