# AWS ECR Setup Guide for GitHub Actions

## Overview

This guide explains how to set up AWS access keys and GitHub secrets/variables for the ECR build and push workflow.

## Prerequisites

- AWS account with appropriate permissions to create IAM users and policies
- GitHub repository admin access
- AWS CLI installed (optional, for verification)

## Step 1: Create an IAM User for GitHub

### Using AWS Console

1. Navigate to **IAM** → **Users**
2. Click **Create user**
3. Enter username: `github-ecr-push` (or any name you prefer)
4. Click **Create user**
5. You'll be taken to the user details page

### Using AWS CLI

```bash
aws iam create-user --user-name github-ecr-push
```

## Step 2: Attach ECR Permissions

### Using AWS Console

1. Open the user you created
2. Go to the **Permissions** tab
3. Click **Add permissions** → **Create inline policy**
4. Select **JSON** editor
5. Replace the default policy with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    }
  ]
}
```

6. Click **Review policy**
7. Name it: `ecr-push-policy`
8. Click **Create policy**

### Using AWS CLI

```bash
aws iam put-user-policy \
  --user-name github-ecr-push \
  --policy-name ecr-push-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ecr:GetAuthorizationToken",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:CreateRepository",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ],
        "Resource": "*"
      }
    ]
  }'
```

## Step 3: Create Access Key

### Using AWS Console

1. With the user open, go to **Security credentials** tab
2. Scroll to **Access keys** section
3. Click **Create access key**
4. Select **Command Line Interface (CLI)** (or use case)
5. Check the confirmation checkbox
6. Click **Create access key**
7. A dialog will show your credentials:
   - **Access Key ID**: Copy this
   - **Secret Access Key**: Copy this (this is the only time you'll see it)
8. Click **Done** and save both values securely

### Using AWS CLI

```bash
aws iam create-access-key --user-name github-ecr-push
```

This will output:
```json
{
  "AccessKey": {
    "UserName": "github-ecr-push",
    "AccessKeyId": "AKIA...",
    "Status": "Active",
    "SecretAccessKey": "xxxxxx...",
    "CreateDate": "2024-11-01T..."
  }
}
```

Save both the `AccessKeyId` and `SecretAccessKey`.

## Step 4: Add GitHub Secrets and Variables

### Setting Secrets in GitHub

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets (one at a time):

#### Secret 1: AWS_ACCESS_KEY_ID
- **Name**: `AWS_ACCESS_KEY_ID`
- **Value**: The Access Key ID from Step 3

#### Secret 2: AWS_SECRET_ACCESS_KEY
- **Name**: `AWS_SECRET_ACCESS_KEY`
- **Value**: The Secret Access Key from Step 3

### Setting Variables in GitHub

1. In the same page (**Settings** → **Secrets and variables** → **Actions**)
2. Click **New repository variable**
3. Add the following variable:

#### Variable 1: AWS_REGION
- **Name**: `AWS_REGION`
- **Value**: Your AWS region (e.g., `us-east-1`, `us-west-2`)

After adding all secrets and variables, you should see:
```
Secrets:
✓ AWS_ACCESS_KEY_ID
✓ AWS_SECRET_ACCESS_KEY

Variables:
✓ AWS_REGION
```

### Why Secrets vs Variables?

- **Secrets** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`): Encrypted, never displayed in logs
- **Variables** (`AWS_REGION`): Public configuration, not sensitive data

This separation follows GitHub best practices for managing sensitive vs non-sensitive configuration.

## Step 5: Verify the Setup

### Check IAM User and Policy

```bash
# Verify user exists
aws iam get-user --user-name github-ecr-push

# List policies for the user
aws iam list-user-policies --user-name github-ecr-push

# View the policy details
aws iam get-user-policy \
  --user-name github-ecr-push \
  --policy-name ecr-push-policy
```

### Test the Workflow

1. Push a commit to the `main` branch:
   ```bash
   git commit --allow-empty -m "Test ECR workflow"
   git push origin main
   ```

2. Go to your GitHub repository **Actions** tab
3. Click on the **Build and Push to AWS ECR** workflow
4. Monitor the execution
5. Check for success or errors

### Verify Images in ECR

Once the workflow completes successfully:

```bash
# List all ECR repositories
aws ecr describe-repositories --region us-east-1

# List images in a specific repository
aws ecr describe-images --repository-name mcp-server-tcp --region us-east-1

# View image details with digests
aws ecr describe-images \
  --repository-name mcp-server-tcp \
  --region us-east-1 \
  --query 'imageDetails[*].{Tag:imageTags, Digest:imageId.imageDigest}'
```

In the AWS Console:
1. Navigate to **ECR** → **Repositories**
2. You should see repositories for each service
3. Click on a repository to see the pushed images

## How Image Detection Works

The workflow uses **Docker image digests** to determine if a push is required:

1. **Local build**: After building with `docker compose build`, the workflow extracts the image digest
2. **ECR latest**: It fetches the digest of the current `latest` tag in ECR
3. **Compare**: If the digests match, the push is skipped (image hasn't changed)
4. **Different digest**: If different (or `latest` doesn't exist), the image is pushed with:
   - Tag: commit SHA (e.g., `abc1234`)
   - Tag: `latest` (always updated)

This approach is more accurate than checking for a specific commit SHA tag because:
- Same source code can produce different images (e.g., dependency changes)
- Digest compares actual image content, not metadata
- Prevents unnecessary pushes of identical images
- Efficiently handles rebuilds and retries

## Troubleshooting

### Credential Error in Workflow

**Error**: `InvalidUserID.AccessDenied: User is not authorized to perform...`

Solutions:
1. Verify secrets are set correctly in GitHub: **Settings** → **Secrets and variables** → **Actions**
2. Make sure secret names are exactly `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (case-sensitive)
3. Check that access key hasn't been deactivated in AWS

### AWS_REGION Not Found

**Error**: `The "aws-region" input is required`

Solutions:
1. Verify AWS_REGION is set as a **Variable** (not a Secret)
2. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
3. Ensure the variable name is exactly `AWS_REGION`

### Access Denied / Permission Error

**Error**: `User: arn:aws:iam::123456789:user/github-ecr-push is not authorized to perform...`

Solutions:
1. Verify the IAM user has the policy attached:
   ```bash
   aws iam list-user-policies --user-name github-ecr-push
   ```

2. Verify the policy includes all required permissions:
   ```bash
   aws iam get-user-policy --user-name github-ecr-push --policy-name ecr-push-policy
   ```

3. If the policy is missing, add it using Step 2

### Invalid Access Key

**Error**: `The AWS Access Key Id you provided does not exist`

Solutions:
1. Verify the Access Key ID is correct in GitHub secrets
2. Check if the access key was accidentally deleted
3. Generate a new access key and update the secrets

### Secret Access Key Not Found

**Error**: `The Security Token included in the request is invalid`

Solutions:
1. Verify the Secret Access Key is correct in GitHub secrets
2. Make sure you copied it exactly (no extra spaces)
3. Access key secrets cannot be recovered - generate a new one if lost

### ECR Repository Creation Failed

**Error**: `AccessDenied: User is not authorized to perform: ecr:CreateRepository`

Solutions:
1. Verify the IAM policy is attached and includes `ecr:CreateRepository`
2. Check your AWS account ECR quota
3. Verify the region specified in AWS_REGION variable is correct

### Image Not Found in ECR

After successful workflow run, images not appearing in ECR:
1. Check the region matches your AWS_REGION variable
2. Verify the workflow completed without errors in the logs
3. Check if image push was skipped due to matching digest (this is normal)

## Security Best Practices

✅ **Rotate access keys periodically** - Create new key, update secrets, delete old key
✅ **Use access key versioning** - Keep track of when keys were created
✅ **Limit IAM policy scope** - This policy is ECR-only (good practice)
✅ **Monitor IAM activity** - Check CloudTrail for access key usage
✅ **Use GitHub secret masking** - Automatic for secrets, prevents logs from showing values
✅ **Never commit secrets** - GitHub Actions provides a safe place to store them
✅ **Use Variables for non-sensitive config** - AWS_REGION is public data

## Managing Access Keys

### List all access keys for a user

```bash
aws iam list-access-keys --user-name github-ecr-push
```

### Deactivate an old access key

```bash
aws iam update-access-key \
  --user-name github-ecr-push \
  --access-key-id AKIA... \
  --status Inactive
```

### Delete an old access key

```bash
aws iam delete-access-key \
  --user-name github-ecr-push \
  --access-key-id AKIA...
```

## References

- [AWS IAM Users](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html)
- [AWS IAM Access Keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html)
- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Variables](https://docs.github.com/en/actions/learn-github-actions/variables)
