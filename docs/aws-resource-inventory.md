# AWS Resource Inventory and Teardown Checklist

This document tracks every AWS resource created for Service Sentinel so the
project can be removed cleanly after the interview. Terraform state is the
machine-readable source of truth; this file is the human-readable checklist.

## Environment

- AWS region: `us-west-1`
- AWS CLI profile used for local deployment: `service-sentinel`
- Terraform configuration directory: `terraform/`
- Terraform state: local and excluded from Git because it can contain sensitive data

Keep the Terraform state available until teardown is complete. Without it,
Terraform cannot reliably identify every resource it created.

## Resource inventory

| Status | AWS service | Resource | Terraform address | Purpose | Cost exposure |
| --- | --- | --- | --- | --- | --- |
| Active—created 2026-08-27 | ECR | `service-sentinel` repository | `aws_ecr_repository.service_sentinel` | Stores immutable Lambda container images | Stored image data and applicable image scanning |
| Active—created 2026-08-28 | IAM | `service-sentinel-api-lambda` role | `aws_iam_role.api_lambda` | Execution identity assumed by the API Lambda | No direct IAM charge |
| Active—created 2026-08-28 | IAM | Basic Lambda logging policy attachment | `aws_iam_role_policy_attachment.api_lambda_basic` | Allows the API Lambda to write CloudWatch logs | No direct IAM charge; log ingestion and storage may incur charges |
| Active—created 2026-08-28 | IAM | `service-sentinel-api-dynamodb-read` inline policy | `aws_iam_role_policy.api_lambda_dynamodb_read` | Allows the API Lambda to read one item from the status table | No direct IAM charge |
| Active—created 2026-08-28 | IAM | `service-sentinel-monitor-lambda` role | `aws_iam_role.monitor_lambda` | Execution identity assumed by the monitor Lambda | No direct IAM charge |
| Active—created 2026-08-28 | IAM | Monitor basic Lambda logging policy attachment | `aws_iam_role_policy_attachment.monitor_lambda_basic` | Allows the monitor Lambda to write CloudWatch logs | No direct IAM charge; log ingestion and storage may incur charges |
| Active—created 2026-08-28 | IAM | `service-sentinel-monitor-dynamodb-write` inline policy | `aws_iam_role_policy.monitor_lambda_dynamodb_write` | Allows only the monitor Lambda to replace the current status item | No direct IAM charge |
| Active—created 2026-08-28 | IAM | `service-sentinel-monitor-scheduler` role | `aws_iam_role.monitor_scheduler` | Identity assumed by EventBridge Scheduler | No direct IAM charge |
| Active—created 2026-08-28 | IAM | `service-sentinel-scheduler-invoke-monitor` inline policy | `aws_iam_role_policy.scheduler_invoke_monitor` | Allows Scheduler to invoke only the monitor production alias | No direct IAM charge |
| Active—created 2026-08-28 | Lambda | `service-sentinel-api` version `1` | `aws_lambda_function.api` | Runs the candidate health API image | Invocation duration, requests, and related logging |
| Active—published 2026-08-28 | Lambda | `service-sentinel-api` version `2` | `aws_lambda_function.api` | Runs the health and status API with DynamoDB configuration | Invocation duration, requests, and related logging |
| Active—published 2026-08-28 | Lambda | `service-sentinel-api` version `3` | `aws_lambda_function.api` | Shared image containing the monitor handler; API candidate smoke tests passed | Invocation duration, requests, and related logging |
| Active—updated 2026-08-28 | Lambda | API `candidate` alias → version `3` | `aws_lambda_alias.candidate` | Smoke-test target before production promotion | No direct alias charge |
| Active—updated 2026-08-28 | Lambda | `production` alias → version `3` | `aws_lambda_alias.production` | Stable target for production API traffic; post-promotion smoke tests passed | No direct alias charge |
| Active—created 2026-08-28 | Lambda | `service-sentinel-monitor` version `1` | `aws_lambda_function.monitor` | Checks the public production health endpoint and writes current status | Invocation duration, requests, outbound API request, and related logging |
| Active—created 2026-08-28 | Lambda | Monitor `candidate` alias → version `1` | `aws_lambda_alias.monitor_candidate` | Direct smoke-test target; candidate invocation passed | No direct alias charge |
| Active—created 2026-08-28 | Lambda | Monitor `production` alias → version `1` | `aws_lambda_alias.monitor_production` | Approved target invoked by EventBridge Scheduler | No direct alias charge |
| Active—created 2026-08-28 | DynamoDB | `service-sentinel-status` table | `aws_dynamodb_table.service_status` | Stores the latest status record for each monitored service | On-demand read/write requests and stored data |
| Active—enabled 2026-08-28 | EventBridge Scheduler | `service-sentinel-monitor` one-minute schedule | `aws_scheduler_schedule.monitor` | Invokes the monitor production alias every minute | Scheduler invocations; expected to remain within the applicable free allowance at this scale |
| Active—created 2026-08-28 | API Gateway | `service-sentinel-api` HTTP API | `aws_apigatewayv2_api.service_sentinel` | Public HTTP entry point | Requests and data transfer |
| Active—created 2026-08-28 | API Gateway | Production Lambda integration | `aws_apigatewayv2_integration.api_lambda` | Sends API requests to the production Lambda alias | Included with API requests |
| Active—created 2026-08-28 | API Gateway | `GET /health` route | `aws_apigatewayv2_route.health` | Exposes the production health endpoint | Included with API requests |
| Active—created 2026-08-28 | API Gateway | `GET /status` route | `aws_apigatewayv2_route.status` | Exposes the latest conservatively evaluated monitoring status | Included with API requests |
| Active—created 2026-08-28 | API Gateway | `$default` stage | `aws_apigatewayv2_stage.default` | Serves `/health` without a stage prefix | Included with API requests |
| Active—created 2026-08-28 | Lambda | API Gateway health invocation permission | `aws_lambda_permission.api_gateway_health` | Allows this API route to invoke the production alias | No direct permission charge |
| Active—created 2026-08-28 | Lambda | API Gateway status invocation permission | `aws_lambda_permission.api_gateway_status` | Allows the status route to invoke the production alias | No direct permission charge |
| Active—AWS-created 2026-08-28 | CloudWatch Logs | `/aws/lambda/service-sentinel-api` | Not yet managed by Terraform | Stores Lambda execution logs; retention is currently unlimited | Log ingestion and indefinite storage until retention is configured |
| Active—AWS-created 2026-08-28 | CloudWatch Logs | `/aws/lambda/service-sentinel-monitor` | Not yet managed by Terraform | Stores monitor execution logs; retention is currently unlimited | Log ingestion and indefinite storage until retention is configured |

## ECR artifacts

Record each pushed image tag and digest here after it is uploaded.

| Image tag | Image digest | Deployment use | Removed |
| --- | --- | --- | --- |
| `929a4c1395cb` | `sha256:9b6635da09d50f40993437f1707f21639cd906dfb4ae94011ec39b5fb257e341` | Lambda version `1`—candidate and production smoke tests passed | No |
| `0fc6f9a11962` | `sha256:604df4500e5c580110b9c0caa06ce9e3fa57fce34c7b71cf811f28dd9e496ff7` | Lambda version `2`—candidate and production smoke tests passed; ECR scan completed successfully | No |
| `8199502e045c` | `sha256:0eb0f9eca850f5e4c1b4beb691d65f50ba713375ff68681268a82b55c50ddec5` | API version `3` candidate/production and monitor version `1`; all smoke tests passed; ECR scan completed with no findings | No |

## Teardown procedure

Do not run these commands until the project is ready to be permanently removed.

1. Authenticate with the intended AWS account and select the `service-sentinel`
   profile.
2. Empty the ECR repository. Terraform is intentionally configured without
   `force_delete`, so it will refuse to destroy a repository that still contains
   images.
3. From the repository root, create and inspect a destruction plan:

   ```powershell
   terraform -chdir=terraform plan -destroy -out=destroy.tfplan
   terraform -chdir=terraform show destroy.tfplan
   ```

4. Confirm that the plan contains only Service Sentinel resources and that every
   proposed action is expected.
5. Apply the reviewed destruction plan:

   ```powershell
   terraform -chdir=terraform apply destroy.tfplan
   ```

6. Confirm in both Terraform and the AWS console that no Service Sentinel
   resources remain.
7. Revoke or remove project-specific AWS access, GitHub OIDC configuration, and
   local credentials only after infrastructure deletion is verified.

## Teardown verification

- [ ] All ECR images removed
- [ ] Terraform destroy plan reviewed
- [ ] Terraform destroy completed successfully
- [ ] AWS console checked for remaining Service Sentinel resources
- [ ] `/aws/lambda/service-sentinel-api` log group removed if it remains unmanaged
- [ ] `/aws/lambda/service-sentinel-monitor` log group removed if it remains unmanaged
- [ ] CloudWatch log groups and other resources not managed by Terraform checked
- [ ] Project-specific IAM and GitHub OIDC access removed
- [ ] Final unexpected-charge check completed in AWS Billing and Cost Management
