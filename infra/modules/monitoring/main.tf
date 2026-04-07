locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# ── CloudWatch Log Group ───────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/finsolve/backend"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.name_prefix}-log-group"
  }
}

# ── SNS Topic for Ops Alerts ───────────────────────────────────────────────────

resource "aws_sns_topic" "ops_alerts" {
  name = "${local.name_prefix}-ops-alerts"

  tags = {
    Name = "${local.name_prefix}-ops-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.ops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── CloudWatch Alarms ──────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "ecs_high_cpu" {
  count = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-high-cpu"
  alarm_description   = "ECS CPU utilisation exceeded 85% — consider scaling up"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  alarm_actions = [aws_sns_topic.ops_alerts.arn]
  ok_actions    = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-ecs-high-cpu"
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_no_tasks" {
  count = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-no-running-tasks"
  alarm_description   = "No ECS tasks are running — service may be down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  alarm_actions = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-ecs-no-running-tasks"
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count = var.alb_arn_suffix != "" ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-5xx-errors"
  alarm_description   = "ALB is returning more than 10 HTTP 5xx errors per 5 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-alb-5xx-errors"
  }
}

# ── Cost & Token Usage Alarms (RC-146, RC-147) ─────────────────────────────────

# RC-146: Alert when estimated daily spend exceeds $5 USD
resource "aws_cloudwatch_metric_alarm" "high_daily_cost" {
  alarm_name          = "${local.name_prefix}-HighDailyCost"
  alarm_description   = "Estimated LLM cost exceeded $${var.daily_cost_threshold_usd}/day — review usage immediately"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCostUSD"
  namespace           = var.token_usage_namespace
  period              = 86400 # 24 hours
  statistic           = "Sum"
  threshold           = var.daily_cost_threshold_usd
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.ops_alerts.arn]
  ok_actions    = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-HighDailyCost"
  }
}

# RC-147: Alert when query volume exceeds 200 requests per hour
resource "aws_cloudwatch_metric_alarm" "high_hourly_queries" {
  alarm_name          = "${local.name_prefix}-HighHourlyQueries"
  alarm_description   = "Query volume exceeded ${var.hourly_query_threshold}/hour — possible abuse or traffic spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RequestCount"
  namespace           = var.token_usage_namespace
  period              = 3600 # 1 hour
  statistic           = "Sum"
  threshold           = var.hourly_query_threshold
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.ops_alerts.arn]
  ok_actions    = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-HighHourlyQueries"
  }
}

# RC-147: Alert when a single request consumes an abnormal number of tokens
resource "aws_cloudwatch_metric_alarm" "abnormal_token_usage" {
  alarm_name          = "${local.name_prefix}-AbnormalTokenUsage"
  alarm_description   = "A single request used more than ${var.token_per_request_threshold} tokens — possible prompt injection or runaway context"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TokensUsed"
  namespace           = var.token_usage_namespace
  period              = 60
  statistic           = "Maximum"
  threshold           = var.token_per_request_threshold
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.ops_alerts.arn]

  tags = {
    Name = "${local.name_prefix}-AbnormalTokenUsage"
  }
}

# ── CloudWatch Dashboard: FinSolveAI-Costs (RC-148, RC-149) ───────────────────

resource "aws_cloudwatch_dashboard" "costs" {
  dashboard_name = "${local.name_prefix}-FinSolveAI-Costs"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1 — Token usage over time by role
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "TokensUsed by Role (hourly)"
          view   = "timeSeries"
          stacked = false
          metrics = [
            for role in ["finance", "hr", "marketing", "engineering", "executive"] :
            ["${var.token_usage_namespace}", "TokensUsed", "Role", role, { "label" : role, "stat" : "Sum", "period" : 3600 }]
          ]
          period = 3600
          region = var.aws_region
          yAxis  = { left = { label = "Tokens", showUnits = false } }
        }
      },
      # Row 1 — Estimated daily cost trend
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "EstimatedCostUSD (daily trend)"
          view   = "timeSeries"
          stacked = false
          metrics = [
            ["${var.token_usage_namespace}", "EstimatedCostUSD", { "label" : "All Roles", "stat" : "Sum", "period" : 86400, "color" : "#ff7f0e" }]
          ]
          period = 86400
          region = var.aws_region
          yAxis  = { left = { label = "USD", showUnits = false } }
          annotations = {
            horizontal = [
              { value = var.daily_cost_threshold_usd, label = "Alert threshold", color = "#d62728" }
            ]
          }
        }
      },
      # Row 2 — Request rate per hour by role
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "RequestCount by Role (hourly)"
          view   = "bar"
          stacked = true
          metrics = [
            for role in ["finance", "hr", "marketing", "engineering", "executive"] :
            ["${var.token_usage_namespace}", "RequestCount", "Role", role, { "label" : role, "stat" : "Sum", "period" : 3600 }]
          ]
          period = 3600
          region = var.aws_region
          yAxis  = { left = { label = "Requests", showUnits = false } }
        }
      },
      # Row 2 — Cost breakdown by role (single period sum)
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "EstimatedCostUSD by Role (daily)"
          view   = "bar"
          stacked = false
          metrics = [
            for role in ["finance", "hr", "marketing", "engineering", "executive"] :
            ["${var.token_usage_namespace}", "EstimatedCostUSD", "Role", role, { "label" : role, "stat" : "Sum", "period" : 86400 }]
          ]
          period = 86400
          region = var.aws_region
          yAxis  = { left = { label = "USD", showUnits = false } }
        }
      },
      # Row 3 — Month-to-date total cost (single-value widget)
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 6
        height = 3
        properties = {
          title  = "Month-to-Date Cost (USD)"
          view   = "singleValue"
          metrics = [
            ["${var.token_usage_namespace}", "EstimatedCostUSD", { "label" : "MTD", "stat" : "Sum", "period" : 2592000, "color" : "#2ca02c" }]
          ]
          region = var.aws_region
        }
      },
      # Row 3 — Peak tokens per request
      {
        type   = "metric"
        x      = 6
        y      = 12
        width  = 6
        height = 3
        properties = {
          title  = "Peak TokensUsed per Request"
          view   = "singleValue"
          metrics = [
            ["${var.token_usage_namespace}", "TokensUsed", { "label" : "Max", "stat" : "Maximum", "period" : 3600, "color" : "#9467bd" }]
          ]
          region = var.aws_region
        }
      },
    ]
  })
}
