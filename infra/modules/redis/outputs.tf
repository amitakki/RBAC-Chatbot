output "primary_endpoint" {
  description = "DNS address of the Redis primary node"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  description = "Port number for Redis connections"
  value       = aws_elasticache_cluster.main.port
}

output "cluster_id" {
  description = "ElastiCache cluster identifier"
  value       = aws_elasticache_cluster.main.id
}
