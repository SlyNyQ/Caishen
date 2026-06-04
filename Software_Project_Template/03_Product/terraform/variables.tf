variable "app_name" {
  description = "Lowercase resource-name prefix."
  type        = string
  default     = "caishen"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.app_name))
    error_message = "App name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  type = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}

variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "ecr_repository_url" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "lambda_memory_size" {
  type    = number
  default = 2048
}

variable "lambda_timeout_seconds" {
  type    = number
  default = 60
}

variable "lambda_architecture" {
  type    = string
  default = "x86_64"

  validation {
    condition     = contains(["x86_64", "arm64"], var.lambda_architecture)
    error_message = "Lambda architecture must be x86_64 or arm64."
  }
}

variable "cloudfront_price_class" {
  type    = string
  default = "PriceClass_100"
}

variable "allow_force_destroy" {
  type    = bool
  default = false
}

variable "default_provider" {
  type    = string
  default = "bedrock"

  validation {
    condition     = contains(["mock", "openai", "anthropic", "google", "bedrock"], var.default_provider)
    error_message = "Default provider must be a supported Caishen provider."
  }
}

variable "use_local_rag" {
  type    = bool
  default = true
}

variable "enable_debug_traces" {
  type    = bool
  default = false
}

variable "openai_model" {
  type    = string
  default = "gpt-4.1-mini"
}

variable "anthropic_model" {
  type    = string
  default = "claude-sonnet-4-5"
}

variable "google_model" {
  type    = string
  default = "gemini-2.0-flash"
}

variable "bedrock_model_id" {
  type    = string
  default = "anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "cors_origins" {
  type    = string
  default = "http://localhost:3000"
}

variable "secret_arns" {
  description = "Secrets Manager ARNs required by optional external providers."
  type        = map(string)
  default     = {}
}

variable "extra_environment" {
  type    = map(string)
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
