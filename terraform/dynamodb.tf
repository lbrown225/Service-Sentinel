resource "aws_dynamodb_table" "service_status" {
  name         = "service-sentinel-status"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "service_name"

  attribute {
    name = "service_name"
    type = "S"
  }
}
