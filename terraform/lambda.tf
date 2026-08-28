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

  depends_on = [
    aws_iam_role_policy_attachment.api_lambda_basic
  ]
}

resource "aws_lambda_alias" "candidate" {
  name             = "candidate"
  description      = "Candidate version awaiting smoke-test approval"
  function_name    = aws_lambda_function.api.function_name
  function_version = aws_lambda_function.api.version
}
