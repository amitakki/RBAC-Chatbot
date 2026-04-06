variable "app_name" {
  description = "Application name prefix for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for ALB and target group"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the Application Load Balancer"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_sg_id" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "ecs_sg_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "task_cpu" {
  description = "Fargate CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Fargate memory in MiB"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Initial number of ECS tasks"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Auto-scaling minimum task count"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Auto-scaling maximum task count"
  type        = number
  default     = 4
}

variable "cpu_scale_target" {
  description = "Target CPU utilisation percentage for auto-scaling"
  type        = number
  default     = 70
}

variable "backend_image_tag" {
  description = "Docker image tag to deploy from ECR"
  type        = string
  default     = "latest"
}

variable "log_group_name" {
  description = "CloudWatch log group name for container logs"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener. Empty = HTTP only."
  type        = string
  default     = ""
}

variable "secret_arns" {
  description = "Map of environment variable names to Secrets Manager ARNs"
  type        = map(string)
}
