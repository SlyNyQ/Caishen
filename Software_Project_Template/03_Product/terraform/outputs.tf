output "api_gateway_url" {
  value = module.lambda_api.api_endpoint
}

output "api_gateway_id" {
  value = module.lambda_api.api_id
}

output "lambda_function_name" {
  value = module.lambda_api.lambda_function_name
}

output "cloudfront_url" {
  value = "https://${module.frontend.cloudfront_domain_name}"
}

output "cloudfront_distribution_id" {
  value = module.frontend.cloudfront_distribution_id
}

output "frontend_bucket_name" {
  value = module.frontend.frontend_bucket_name
}
