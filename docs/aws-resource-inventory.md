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

## ECR artifacts

Record each pushed image tag and digest here after it is uploaded.

| Image tag | Image digest | Deployment use | Removed |
| --- | --- | --- | --- |
| None yet | None yet | None yet | Not applicable |

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
- [ ] CloudWatch log groups and other resources not managed by Terraform checked
- [ ] Project-specific IAM and GitHub OIDC access removed
- [ ] Final unexpected-charge check completed in AWS Billing and Cost Management
