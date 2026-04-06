# ── AWS Amplify Frontend Deployment ───────────────────────────────────────────
# Connects to the GitHub repository, builds the React/Vite app, and hosts it.
# VITE_API_BASE_URL is set to the ALB DNS name so the frontend calls the backend.

resource "aws_amplify_app" "frontend" {
  name         = "${local.name_prefix}-frontend"
  repository   = var.amplify_github_repo
  access_token = var.amplify_github_token

  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: frontend/dist
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
  EOT

  environment_variables = {
    VITE_API_BASE_URL = "http://${module.ecs.alb_dns_name}"
    NODE_ENV          = "production"
  }

  # SPA rewrite: serve index.html for all routes that are not static assets
  custom_rule {
    source = "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>"
    target = "/index.html"
    status = "200"
  }

  tags = {
    Name = "${local.name_prefix}-frontend"
  }
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.frontend.id
  branch_name = var.amplify_branch

  enable_auto_build           = true
  enable_pull_request_preview = false

  stage = var.environment == "production" ? "PRODUCTION" : "STAGING"

  environment_variables = {
    # Branch-level override: use HTTPS if certificate_arn is configured
    VITE_API_BASE_URL = var.certificate_arn != "" ? "https://${module.ecs.alb_dns_name}" : "http://${module.ecs.alb_dns_name}"
  }

  tags = {
    Name = "${local.name_prefix}-frontend-${var.amplify_branch}"
  }
}
