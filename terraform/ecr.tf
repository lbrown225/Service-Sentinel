resource "aws_ecr_repository" "service_sentinel" {
  name                 = "service-sentinel"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}
