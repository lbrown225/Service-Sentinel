data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_lambda" {
  name               = "service-sentinel-api-lambda"
  description        = "Execution role for the Service Sentinel API Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "api_lambda_basic" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "api_lambda_dynamodb_read" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.service_status.arn]
  }
}

resource "aws_iam_role_policy" "api_lambda_dynamodb_read" {
  name   = "service-sentinel-api-dynamodb-read"
  role   = aws_iam_role.api_lambda.name
  policy = data.aws_iam_policy_document.api_lambda_dynamodb_read.json
}
