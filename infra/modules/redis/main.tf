locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# ── ElastiCache Subnet Group ───────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name        = "${local.name_prefix}-redis-subnet-group"
  description = "Private subnets for FinSolve Redis cluster"
  subnet_ids  = var.subnet_ids

  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# ── ElastiCache Redis Cluster ──────────────────────────────────────────────────

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  node_type            = var.node_type
  num_cache_nodes      = 1
  engine_version       = var.engine_version
  port                 = 6379
  parameter_group_name = "default.redis7"

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [var.redis_sg_id]

  # Daily automated snapshot (ElastiCache does not support sub-hourly RDB snapshots)
  snapshot_retention_limit = 1
  snapshot_window          = "05:00-06:00"
  maintenance_window       = "sun:06:00-sun:07:00"

  apply_immediately = true

  tags = {
    Name = "${local.name_prefix}-redis"
  }
}
