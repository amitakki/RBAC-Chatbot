output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer — use as VITE_API_BASE_URL in Amplify"
  value       = module.ecs.alb_dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL — used in CI/CD docker push commands"
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name — used in deploy scripts and GitHub Actions"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name — used in deploy scripts and GitHub Actions"
  value       = module.ecs.service_name
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint — update REDIS_URL secret post-apply"
  value       = module.redis.primary_endpoint
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = module.redis.port
}

output "amplify_default_domain" {
  description = "Default AWS Amplify domain for the frontend"
  value       = "https://${var.amplify_branch}.${aws_amplify_app.frontend.id}.amplifyapp.com"
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name — use for log tail commands"
  value       = module.monitoring.log_group_name
}

output "sns_ops_topic_arn" {
  description = "SNS topic ARN for ops alarm notifications"
  value       = module.monitoring.sns_topic_arn
}
