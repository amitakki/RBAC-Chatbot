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
