# Caishen Terraform Guide

The active environment stack is intentionally small:

```text
modules/lambda_api            FastAPI container on Lambda + API Gateway
modules/frontend_cloudfront   private S3 static site + CloudFront + /api routing
```

There are no ECS, VPC/network, or separate task-IAM modules. The Lambda module owns its least-privilege execution role and grants log writing, Bedrock invocation, and optional named Secrets Manager reads.

## Inputs

Required:

- `environment`: `dev`, `test`, or `prod`
- `ecr_repository_url`: repository containing the backend Lambda image
- `image_tag`: immutable or reviewed image tag

Important defaults:

- `app_name = "caishen"`
- `aws_region = "eu-west-2"`
- `default_provider = "bedrock"`
- `use_local_rag = true`
- `enable_debug_traces = false`

Use `terraform.tfvars.example` as a sanitized starting point. Keep real local values, backend configuration, state, and state backups outside version control.

## Validate Without Remote State

```powershell
terraform init -backend=false -reconfigure
terraform fmt -check -recursive
terraform validate
```

## Plan

```powershell
terraform init `
  -backend-config="bucket=<state-bucket>" `
  -backend-config="key=environments/dev/terraform.tfstate" `
  -backend-config="region=eu-west-2" `
  -backend-config="dynamodb_table=<lock-table>"
terraform plan -var-file="local.dev.tfvars"
```

Do not apply or destroy automatically. Existing resources with older names require an explicit import, state move, or replacement decision.

## Bootstrap

`bootstrap/` is optional and separately stateful. It can provision the remote-state bucket, lock table, ECR repository, and archival KB buckets. Its defaults and examples use the `caishen` slug. Those shared resources must not be destroyed as part of a normal environment teardown.
