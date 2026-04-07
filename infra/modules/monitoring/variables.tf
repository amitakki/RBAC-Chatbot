variable "app_name" {
  description = "Application name prefix for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "ecs_cluster_name" {
  description = "ECS cluster name for CloudWatch alarm dimensions"
  type        = string
  default     = ""
}

variable "ecs_service_name" {
  description = "ECS service name for CloudWatch alarm dimensions"
  type        = string
  default     = ""
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for CloudWatch alarm dimensions"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email for SNS alarm notifications. Leave empty to skip subscription."
  type        = string
  default     = ""
}

# ── Cost & Token Usage (RC-146, RC-147, RC-148, RC-149) ───────────────────────

variable "token_usage_namespace" {
  description = "CloudWatch custom metric namespace used by the backend for token/cost metrics"
  type        = string
  default     = "FinSolveAI/TokenUsage"
}

variable "daily_cost_threshold_usd" {
  description = "USD amount at which the HighDailyCost alarm fires (daily EstimatedCostUSD sum)"
  type        = number
  default     = 5
}

variable "hourly_query_threshold" {
  description = "Number of requests per hour at which the HighHourlyQueries alarm fires"
  type        = number
  default     = 200
}

variable "token_per_request_threshold" {
  description = "Maximum tokens per single request before the AbnormalTokenUsage alarm fires"
  type        = number
  default     = 4000
}

variable "aws_region" {
  description = "AWS region used in the CloudWatch dashboard widget definitions"
  type        = string
  default     = "us-east-1"
}
