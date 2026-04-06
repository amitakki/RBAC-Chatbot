output "groq_api_key_arn" {
  description = "ARN of the GROQ_API_KEY secret"
  value       = aws_secretsmanager_secret.groq_api_key.arn
}

output "qdrant_api_key_arn" {
  description = "ARN of the QDRANT_API_KEY secret"
  value       = aws_secretsmanager_secret.qdrant_api_key.arn
}

output "jwt_secret_arn" {
  description = "ARN of the JWT_SECRET secret"
  value       = aws_secretsmanager_secret.jwt_secret.arn
}

output "langsmith_api_key_arn" {
  description = "ARN of the LANGSMITH_API_KEY secret"
  value       = aws_secretsmanager_secret.langsmith_api_key.arn
}

output "qdrant_url_arn" {
  description = "ARN of the QDRANT_URL secret"
  value       = aws_secretsmanager_secret.qdrant_url.arn
}

output "qdrant_collection_arn" {
  description = "ARN of the QDRANT_COLLECTION secret"
  value       = aws_secretsmanager_secret.qdrant_collection.arn
}

output "redis_url_arn" {
  description = "ARN of the REDIS_URL secret (update after ElastiCache is provisioned)"
  value       = aws_secretsmanager_secret.redis_url.arn
}

output "embedding_model_arn" {
  description = "ARN of the EMBEDDING_MODEL secret"
  value       = aws_secretsmanager_secret.embedding_model.arn
}

output "langsmith_project_arn" {
  description = "ARN of the LANGSMITH_PROJECT secret"
  value       = aws_secretsmanager_secret.langsmith_project.arn
}
