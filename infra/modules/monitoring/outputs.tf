output "log_group_name" {
  description = "Name of the CloudWatch log group for the backend"
  value       = aws_cloudwatch_log_group.backend.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.backend.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS ops-alerts topic"
  value       = aws_sns_topic.ops_alerts.arn
}
