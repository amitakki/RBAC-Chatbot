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
