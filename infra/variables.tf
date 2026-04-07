variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (staging or production)"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "app_name" {
  description = "Application name, used as prefix for all resource names"
  type        = string
  default     = "finsolve"
}

# ── Networking ─────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the 2 public subnets (ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly 2 public subnet CIDRs are required."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the 2 private subnets (ECS + Redis)"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly 2 private subnet CIDRs are required."
  }
}

variable "availability_zones" {
  description = "Availability zones for subnet placement"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly 2 availability zones are required."
  }
}

# ── ECS / Compute ──────────────────────────────────────────────────────────────

variable "backend_image_tag" {
  description = "ECR image tag to deploy on ECS"
  type        = string
  default     = "latest"
}

variable "ecs_task_cpu" {
  description = "Fargate CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_task_memory" {
  description = "Fargate memory in MiB (2048 = 2 GB)"
  type        = number
  default     = 2048
}

variable "ecs_desired_count" {
  description = "Initial number of ECS tasks"
  type        = number
  default     = 1
}

variable "ecs_min_capacity" {
  description = "Auto-scaling minimum number of tasks"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Auto-scaling maximum number of tasks"
  type        = number
  default     = 4
}

variable "ecs_cpu_scale_target" {
  description = "CPU utilisation percentage target for auto-scaling"
  type        = number
  default     = 70
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Leave empty to use HTTP only (e.g. staging without a domain)."
  type        = string
  default     = ""
}

# ── Redis / ElastiCache ────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.2"
}

# ── Monitoring ─────────────────────────────────────────────────────────────────

variable "log_retention_days" {
  description = "CloudWatch log group retention period in days"
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Email address to receive CloudWatch alarm notifications. Leave empty to skip email subscription."
  type        = string
  default     = ""
}

variable "token_usage_namespace" {
  description = "CloudWatch custom metric namespace for token/cost metrics"
  type        = string
  default     = "FinSolveAI/TokenUsage"
}

variable "daily_cost_threshold_usd" {
  description = "USD daily spend threshold for the HighDailyCost alarm"
  type        = number
  default     = 5
}

variable "hourly_query_threshold" {
  description = "Requests per hour threshold for the HighHourlyQueries alarm"
  type        = number
  default     = 200
}

variable "token_per_request_threshold" {
  description = "Max tokens per request before the AbnormalTokenUsage alarm fires"
  type        = number
  default     = 4000
}

# ── Amplify / Frontend ─────────────────────────────────────────────────────────

variable "amplify_github_repo" {
  description = "Full HTTPS GitHub repository URL for Amplify (e.g. https://github.com/org/repo)"
  type        = string
}

variable "amplify_branch" {
  description = "Git branch that Amplify tracks and deploys"
  type        = string
  default     = "main"
}

variable "amplify_github_token" {
  description = "GitHub Personal Access Token with repo scope for Amplify access"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.amplify_github_token) > 0
    error_message = "amplify_github_token must not be empty."
  }
}
