provider "aws" {
  region = var.region
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.61.0"
    }
  }
  required_version = ">= 1.0.0"
}


data "aws_caller_identity" "current" {}

data "aws_ecr_authorization_token" "ecr_token" {}


resource "aws_s3_bucket" "model_bucket" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_object" "model_object" {
  bucket  = aws_s3_bucket.model_bucket.bucket
  key     = "model.pkl"
  source = "${path.module}/../model/model.pkl"
}

resource "aws_dynamodb_table" "survivors" {
  name         = "survivors"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name = "survivors-table"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "s3_access_policy" {
  name        = "s3_access_policy"
  description = "Policy for Lambda to access S3 bucket"
  policy      = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          "${aws_s3_bucket.model_bucket.arn}",
          "${aws_s3_bucket.model_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_policy_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}


resource "aws_lambda_function" "ml_model" {
  function_name = "ml_model"
  role          = aws_iam_role.lambda_exec.arn
  image_uri      = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_repository_name}:v0.6"
  package_type   = "Image"
  timeout       = 15
  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.survivors.name
      S3_BUCKET_NAME = aws_s3_bucket.model_bucket.bucket
      S3_MODEL_KEY   = aws_s3_object.model_object.key
    }
  }
}


# Policy for Lambda to access DynamoDB and other resources
resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "lambda_dynamodb_policy"
  description = "IAM policy for Lambda to access DynamoDB table"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ],
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject"
        ],
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "lambda_dynamodb_policy_attachment" {
  name       = "lambda_dynamodb_policy_attachment"
  roles      = [aws_iam_role.lambda_exec.name]
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

resource "aws_api_gateway_rest_api" "ml_api" {
  name        = "ml_api"
  description = "API for Titanic survivors prediction"
}

resource "aws_api_gateway_resource" "survivor_resource" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  parent_id   = aws_api_gateway_rest_api.ml_api.root_resource_id
  path_part   = "sobreviventes"
}

resource "aws_api_gateway_method" "post_method" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_resource.survivor_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_integration" {
  rest_api_id             = aws_api_gateway_rest_api.ml_api.id
  resource_id             = aws_api_gateway_resource.survivor_resource.id
  http_method             = aws_api_gateway_method.post_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.ml_model.arn}/invocations"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ml_model.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.ml_api.execution_arn}/*/*"
}

resource "aws_api_gateway_method_response" "post_method_response" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.post_method.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "post_integration_response" {
  depends_on  = [aws_api_gateway_integration.post_integration]
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.post_method.http_method
  status_code = aws_api_gateway_method_response.post_method_response.status_code
  selection_pattern = "2.."
}

resource "aws_api_gateway_deployment" "api_deployment" {
  depends_on = [
    aws_api_gateway_integration.post_integration,
    aws_api_gateway_integration.get_integration,
    aws_api_gateway_integration.delete_integration,
    aws_api_gateway_integration.health_integration
  ]
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  stage_name  = "prod"
}

resource "aws_api_gateway_method" "get_method" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_resource.survivor_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_integration" {
  rest_api_id             = aws_api_gateway_rest_api.ml_api.id
  resource_id             = aws_api_gateway_resource.survivor_resource.id
  http_method             = aws_api_gateway_method.get_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.ml_model.arn}/invocations"
}

# Método GET para o recurso /health
resource "aws_api_gateway_method" "health_get_method" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_resource.health_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "get_method_response" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.get_method.http_method
  status_code = "200"
}

# Criação do recurso /health
resource "aws_api_gateway_resource" "health_resource" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  parent_id   = aws_api_gateway_rest_api.ml_api.root_resource_id
  path_part   = "health"
}

# Integração Lambda com o método GET para /health
resource "aws_api_gateway_integration" "health_integration" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.health_resource.id
  http_method = aws_api_gateway_method.health_get_method.http_method
  type = "AWS_PROXY"
  integration_http_method = "POST"
  uri = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.ml_model.arn}/invocations"
}

# Criação do método de resposta para o GET /health
resource "aws_api_gateway_method_response" "health_get_method_response" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.health_resource.id
  http_method = aws_api_gateway_method.health_get_method.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "get_integration_response" {
  depends_on  = [aws_api_gateway_integration.get_integration]
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.get_method.http_method
  status_code = aws_api_gateway_method_response.get_method_response.status_code
  selection_pattern = "2.."
}

resource "aws_api_gateway_method" "delete_method" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_resource.survivor_resource.id
  http_method   = "DELETE"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "delete_integration" {
  rest_api_id             = aws_api_gateway_rest_api.ml_api.id
  resource_id             = aws_api_gateway_resource.survivor_resource.id
  http_method             = aws_api_gateway_method.delete_method.http_method
  integration_http_method = "DELETE"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.ml_model.arn}/invocations"
}

resource "aws_api_gateway_method_response" "delete_method_response" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.delete_method.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "delete_integration_response" {
  depends_on  = [aws_api_gateway_integration.delete_integration]
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.survivor_resource.id
  http_method = aws_api_gateway_method.delete_method.http_method
  status_code = aws_api_gateway_method_response.delete_method_response.status_code
  selection_pattern = "2.."
}
