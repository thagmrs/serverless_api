# Outputs esperados ao final da construção

output "api_url" {
  value = aws_api_gateway_stage.my_api_stage.invoke_url
}

output "swagger_url" {
  value = "${aws_api_gateway_stage.my_api_stage.invoke_url}/doc"
}