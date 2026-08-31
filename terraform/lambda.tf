data "aws_ecr_image" "candidate" {
  repository_name = aws_ecr_repository.service_sentinel.name
  image_tag       = var.candidate_image_tag
}

resource "aws_lambda_function" "api" {
  function_name = "service-sentinel-api"
  description   = "Service Sentinel health API"
  role          = aws_iam_role.api_lambda.arn

  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.service_sentinel.repository_url}@${data.aws_ecr_image.candidate.image_digest}"
  architectures = ["x86_64"]

  memory_size = 256
  timeout     = 10
  publish     = true

  environment {
    variables = {
      STATUS_STALE_AFTER_SECONDS = "300"
      STATUS_TABLE_NAME          = aws_dynamodb_table.service_status.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.api_lambda_basic,
    aws_iam_role_policy.api_lambda_dynamodb_read
  ]

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "monitor" {
  function_name = "service-sentinel-monitor"
  description   = "Service Sentinel health monitor"
  role          = aws_iam_role.monitor_lambda.arn

  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.service_sentinel.repository_url}@${data.aws_ecr_image.candidate.image_digest}"
  architectures = ["x86_64"]

  image_config {
    command = ["service_sentinel.monitor.handler"]
  }

  memory_size = 256
  timeout     = 15
  publish     = true

  environment {
    variables = {
      HEALTH_ENDPOINT              = "${aws_apigatewayv2_api.service_sentinel.api_endpoint}/health"
      HEALTH_CHECK_TIMEOUT_SECONDS = "5"
      STATUS_TABLE_NAME            = aws_dynamodb_table.service_status.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.monitor_lambda_basic,
    aws_iam_role_policy.monitor_lambda_dynamodb_write,
    aws_iam_role_policy.monitor_lambda_cloudwatch_metrics
  ]

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_alias" "monitor_candidate" {
  name             = "candidate"
  description      = "Candidate monitor version awaiting smoke-test approval"
  function_name    = aws_lambda_function.monitor.function_name
  function_version = aws_lambda_function.monitor.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_alias" "monitor_production" {
  name             = "production"
  description      = "Production monitor version for scheduled health checks"
  function_name    = aws_lambda_function.monitor.function_name
  function_version = aws_lambda_function.monitor.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_alias" "candidate" {
  name             = "candidate"
  description      = "Candidate version awaiting smoke-test approval"
  function_name    = aws_lambda_function.api.function_name
  function_version = aws_lambda_function.api.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_alias" "production" {
  name             = "production"
  description      = "Production version serving API Gateway traffic"
  function_name    = aws_lambda_function.api.function_name
  function_version = aws_lambda_function.api.version

  lifecycle {
    ignore_changes = [function_version]
  }
}
