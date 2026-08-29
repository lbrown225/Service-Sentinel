resource "aws_scheduler_schedule" "monitor" {
  name        = "service-sentinel-monitor"
  description = "Invoke the Service Sentinel monitor every minute"
  state       = var.monitor_schedule_enabled ? "ENABLED" : "DISABLED"

  schedule_expression = "rate(1 minute)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_alias.monitor_production.arn
    role_arn = aws_iam_role.monitor_scheduler.arn
  }

  depends_on = [aws_iam_role_policy.scheduler_invoke_monitor]
}
