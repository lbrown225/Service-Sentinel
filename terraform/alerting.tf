resource "aws_sns_topic" "health_alerts" {
  name = "service-sentinel-health-alerts"
}

resource "aws_sns_topic_subscription" "health_alert_email" {
  count = var.alert_email == null ? 0 : 1

  topic_arn = aws_sns_topic.health_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "service_unhealthy" {
  alarm_name        = "service-sentinel-health-check-failed"
  alarm_description = "The service is unhealthy or the monitor has stopped publishing data."

  namespace           = "ServiceSentinel"
  metric_name         = "HealthCheckSuccess"
  dimensions          = { Service = "service-sentinel-api" }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2

  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.health_alerts.arn]
}

data "aws_iam_policy_document" "health_alert_topic" {
  statement {
    sid     = "AllowCloudWatchAlarmPublish"
    effect  = "Allow"
    actions = ["sns:Publish"]
    resources = [
      aws_sns_topic.health_alerts.arn,
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_metric_alarm.service_unhealthy.arn]
    }
  }
}

resource "aws_sns_topic_policy" "health_alerts" {
  arn    = aws_sns_topic.health_alerts.arn
  policy = data.aws_iam_policy_document.health_alert_topic.json
}
