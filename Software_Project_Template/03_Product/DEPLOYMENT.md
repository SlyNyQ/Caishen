# Caishen Deployment

The active deployment path is:

```text
backend/Dockerfile.lambda -> ECR -> Lambda -> API Gateway
frontend/out              -> private S3 -> CloudFront
CloudFront /api/*         -> API Gateway
```

The Lambda image builds the Caishen Markdown knowledge base into local retrieval chunks. Provider credentials remain server-side. Bedrock can use the Lambda execution role; external provider keys should be supplied through a secrets workflow and injected as environment variables.

## Prerequisites

- Terraform 1.7 or newer
- Docker
- AWS CLI credentials or an assumed deployment role
- An ECR repository containing the backend image
- A remote-state S3 bucket and DynamoDB lock table

Do not apply or destroy infrastructure automatically as part of local verification. Renaming from older resource prefixes requires an explicit state-migration or replacement plan.

## Build

```powershell
docker build -f backend\Dockerfile.lambda -t caishen-backend:local .
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="/api"
npm run build
```

Push the image to ECR before applying Terraform. The static export is written to `frontend/out`.

## Terraform

Copy `terraform/terraform.tfvars.example` to an ignored local file and replace placeholders. Then:

```powershell
cd terraform
terraform init -backend-config="bucket=<state-bucket>" `
  -backend-config="key=environments/dev/terraform.tfstate" `
  -backend-config="region=eu-west-2" `
  -backend-config="dynamodb_table=<lock-table>"
terraform plan -var-file="local.dev.tfvars"
```

Run `terraform apply` only after reviewing the plan and deciding how existing differently named resources should migrate.

After an approved apply, publish the frontend and invalidate CloudFront:

```powershell
aws s3 sync frontend\out "s3://<frontend-bucket>" --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

## Smoke Checks

Verify:

- `/api/health` reports `app: caishen`
- `/api/ready` reports the configured default provider
- `/api/chat` returns structured `analysis`
- trade execution and personalized buy/sell directives are refused
- unavailable market data is explicitly marked unavailable
