resource "aws_apigatewayv2_api" "service_sentinel" {
  name          = "service-sentinel-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id                 = aws_apigatewayv2_api.service_sentinel.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_alias.production.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.service_sentinel.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.service_sentinel.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway_health" {
  statement_id  = "AllowApiGatewayInvokeProductionHealth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  qualifier     = aws_lambda_alias.production.name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.service_sentinel.execution_arn}/*/GET/health"
}
