#variavel de regiao onde os rescursos serao criados
variable "region" {
  description = "AWS region"
  default     = "us-west-2"
}

#variavel que define o nome da tabela do dynamo
variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  default     = "survivors"
}

#variavel que define o nome do bucket s3
variable "s3_bucket_name" {
  description = "The name of the S3 bucket to store the model and layer"
  type        = string
  default     = "bucket-case-model"
}

#variavel que define o nome do repositorio do ECR onde se encontra a imagem docker a ser utilizada
variable "ecr_repository_name" {
  description = "The name of the ECR repository"
  default     = "img_docker"
}


