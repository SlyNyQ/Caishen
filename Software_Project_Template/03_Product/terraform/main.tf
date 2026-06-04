locals {
  base_tags = merge(
    {
      Project     = var.app_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Runtime     = "lambda"
    },
    var.tags
  )

  force_destroy   = var.allow_force_destroy || var.environment != "prod"
  container_image = "${var.ecr_repository_url}:${var.image_tag}"
  app_environment = merge(
    {
      APP_NAME            = var.app_name
      APP_ENV             = var.environment
      LOG_LEVEL           = "INFO"
      CORS_ORIGINS        = var.cors_origins
      DEFAULT_PROVIDER    = var.default_provider
      USE_LOCAL_RAG       = tostring(var.use_local_rag)
      ENABLE_DEBUG_TRACES = tostring(var.enable_debug_traces)
      OPENAI_MODEL        = var.openai_model
      ANTHROPIC_MODEL     = var.anthropic_model
      GOOGLE_MODEL        = var.google_model
      BEDROCK_MODEL_ID    = var.bedrock_model_id
      AWS_REGION          = var.aws_region
    },
    var.extra_environment
  )
}

module "lambda_api" {
  source = "./modules/lambda_api"

  app_name              = var.app_name
  environment           = var.environment
  image_uri             = local.container_image
  memory_size           = var.lambda_memory_size
  timeout_seconds       = var.lambda_timeout_seconds
  architecture          = var.lambda_architecture
  environment_variables = local.app_environment
  secret_arns           = var.secret_arns
  tags                  = local.base_tags
}

module "frontend" {
  source = "./modules/frontend_cloudfront"

  app_name        = var.app_name
  environment     = var.environment
  api_gateway_url = module.lambda_api.api_endpoint
  force_destroy   = local.force_destroy
  price_class     = var.cloudfront_price_class
  tags            = local.base_tags
}
