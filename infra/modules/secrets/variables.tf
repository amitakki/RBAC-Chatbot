variable "app_name" {
  description = "Application name prefix for secret naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment (used in secret path)"
  type        = string
}
