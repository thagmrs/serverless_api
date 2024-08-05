variable "region" {
  description = "AWS region"
  default     = "us-west-2"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  default     = "survivors"
}

variable "s3_bucket_name" {
  description = "The name of the S3 bucket to store the model and layer"
  type        = string
  default     = "bucket-case-model"
}

variable "ecr_repository_name" {
  description = "The name of the ECR repository"
  default     = "img_docker"
}