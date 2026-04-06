locals {
  secret_path = "${var.app_name}/${var.environment}"
}

# ── Secret definitions ─────────────────────────────────────────────────────────
# recovery_window_in_days = 0 allows immediate deletion on terraform destroy (staging).
# Update secret values manually or via CI/CD after first apply.

resource "aws_secretsmanager_secret" "groq_api_key" {
  name                    = "${local.secret_path}/GROQ_API_KEY"
  description             = "Groq LLM API key for FinSolve chatbot"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/GROQ_API_KEY"
  }
}

resource "aws_secretsmanager_secret_version" "groq_api_key" {
  secret_id     = aws_secretsmanager_secret.groq_api_key.id
  secret_string = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "qdrant_api_key" {
  name                    = "${local.secret_path}/QDRANT_API_KEY"
  description             = "Qdrant Cloud API key"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/QDRANT_API_KEY"
  }
}

resource "aws_secretsmanager_secret_version" "qdrant_api_key" {
  secret_id     = aws_secretsmanager_secret.qdrant_api_key.id
  secret_string = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "${local.secret_path}/JWT_SECRET"
  description             = "HS256 JWT signing secret"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/JWT_SECRET"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "langsmith_api_key" {
  name                    = "${local.secret_path}/LANGSMITH_API_KEY"
  description             = "LangSmith tracing API key"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/LANGSMITH_API_KEY"
  }
}

resource "aws_secretsmanager_secret_version" "langsmith_api_key" {
  secret_id     = aws_secretsmanager_secret.langsmith_api_key.id
  secret_string = "REPLACE_ME"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "qdrant_url" {
  name                    = "${local.secret_path}/QDRANT_URL"
  description             = "Qdrant Cloud cluster HTTPS URL"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/QDRANT_URL"
  }
}

resource "aws_secretsmanager_secret_version" "qdrant_url" {
  secret_id     = aws_secretsmanager_secret.qdrant_url.id
  secret_string = "https://REPLACE_ME.qdrant.io:6333"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "qdrant_collection" {
  name                    = "${local.secret_path}/QDRANT_COLLECTION"
  description             = "Qdrant collection name for document chunks"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/QDRANT_COLLECTION"
  }
}

resource "aws_secretsmanager_secret_version" "qdrant_collection" {
  secret_id     = aws_secretsmanager_secret.qdrant_collection.id
  secret_string = "finsolve_docs"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "redis_url" {
  name                    = "${local.secret_path}/REDIS_URL"
  description             = "Redis connection URL — update with ElastiCache endpoint after first apply"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/REDIS_URL"
  }
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id     = aws_secretsmanager_secret.redis_url.id
  secret_string = "redis://REPLACE_ME:6379"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "embedding_model" {
  name                    = "${local.secret_path}/EMBEDDING_MODEL"
  description             = "HuggingFace embedding model identifier"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/EMBEDDING_MODEL"
  }
}

resource "aws_secretsmanager_secret_version" "embedding_model" {
  secret_id     = aws_secretsmanager_secret.embedding_model.id
  secret_string = "sentence-transformers/all-MiniLM-L6-v2"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "langsmith_project" {
  name                    = "${local.secret_path}/LANGSMITH_PROJECT"
  description             = "LangSmith project name for trace grouping"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.secret_path}/LANGSMITH_PROJECT"
  }
}

resource "aws_secretsmanager_secret_version" "langsmith_project" {
  secret_id     = aws_secretsmanager_secret.langsmith_project.id
  secret_string = "finsolve-chatbot"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
