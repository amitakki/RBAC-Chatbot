locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# ── Networking ─────────────────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  app_name             = var.app_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = var.availability_zones
}

# ── Secrets Manager ────────────────────────────────────────────────────────────

module "secrets" {
  source = "./modules/secrets"

  app_name    = var.app_name
  environment = var.environment
}

# ── Monitoring ─────────────────────────────────────────────────────────────────
# Created before ECS so the log group ARN is available for the task definition.
# ECS-specific alarm dimensions are passed after ECS outputs are known.

module "monitoring" {
  source = "./modules/monitoring"

  app_name           = var.app_name
  environment        = var.environment
  log_retention_days = var.log_retention_days
  alert_email        = var.alert_email

  # Wired after ECS module resolves — Terraform resolves the DAG automatically
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_name = module.ecs.service_name
  alb_arn_suffix   = module.ecs.alb_arn_suffix
}

# ── Redis (ElastiCache) ────────────────────────────────────────────────────────

module "redis" {
  source = "./modules/redis"

  app_name       = var.app_name
  environment    = var.environment
  subnet_ids     = module.networking.private_subnet_ids
  redis_sg_id    = module.networking.redis_sg_id
  node_type      = var.redis_node_type
  engine_version = var.redis_engine_version
}

# ── ECS (Fargate + ALB + ECR + Auto-scaling) ───────────────────────────────────

module "ecs" {
  source = "./modules/ecs"

  app_name           = var.app_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  alb_sg_id          = module.networking.alb_sg_id
  ecs_sg_id          = module.networking.ecs_sg_id

  task_cpu         = var.ecs_task_cpu
  task_memory      = var.ecs_task_memory
  desired_count    = var.ecs_desired_count
  min_capacity     = var.ecs_min_capacity
  max_capacity     = var.ecs_max_capacity
  cpu_scale_target = var.ecs_cpu_scale_target
  backend_image_tag = var.backend_image_tag
  certificate_arn  = var.certificate_arn

  log_group_name = module.monitoring.log_group_name

  secret_arns = {
    GROQ_API_KEY        = module.secrets.groq_api_key_arn
    QDRANT_API_KEY      = module.secrets.qdrant_api_key_arn
    JWT_SECRET          = module.secrets.jwt_secret_arn
    LANGSMITH_API_KEY   = module.secrets.langsmith_api_key_arn
    QDRANT_URL          = module.secrets.qdrant_url_arn
    QDRANT_COLLECTION   = module.secrets.qdrant_collection_arn
    REDIS_URL           = module.secrets.redis_url_arn
    EMBEDDING_MODEL     = module.secrets.embedding_model_arn
    LANGSMITH_PROJECT   = module.secrets.langsmith_project_arn
  }
}
