resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:lbrown225@124473347/Service-Sentinel@1346843051:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "service-sentinel-github-actions-deploy"
  description        = "Deployment role assumed by Service Sentinel GitHub Actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "github_actions_deploy" {
  statement {
    sid       = "GetEcrAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PushServiceSentinelImage"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImageScanFindings",
      "ecr:DescribeImages",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:BatchGetImage",
      "ecr:UploadLayerPart"
    ]
    resources = [aws_ecr_repository.service_sentinel.arn]
  }

  statement {
    sid    = "DeployServiceSentinelFunctions"
    effect = "Allow"
    actions = [
      "lambda:GetFunctionConfiguration",
      "lambda:PublishVersion",
      "lambda:GetFunction",
      "lambda:UpdateFunctionCode"
    ]
    resources = [
      aws_lambda_function.api.arn,
      aws_lambda_function.monitor.arn
    ]
  }

  statement {
    sid    = "TestAndPromoteServiceSentinelAliases"
    effect = "Allow"
    actions = [
      "lambda:GetAlias",
      "lambda:InvokeFunction",
      "lambda:UpdateAlias"
    ]
    resources = [
      aws_lambda_alias.candidate.arn,
      aws_lambda_alias.production.arn,
      aws_lambda_alias.monitor_candidate.arn,
      aws_lambda_alias.monitor_production.arn
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "service-sentinel-github-actions-deploy"
  role   = aws_iam_role.github_actions_deploy.name
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}
