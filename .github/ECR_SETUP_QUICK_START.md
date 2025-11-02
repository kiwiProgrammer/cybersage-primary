# ECR Setup Quick Start

## 5-Minute Setup

### Step 1: Create IAM User for GitHub

In the AWS Console:

1. Navigate to **IAM** → **Users**
2. Click **Create user**
3. Name: `github-ecr-push` (or your preferred name)
4. Click **Create user**

### Step 2: Attach ECR Permissions

1. Open the user you just created
2. Go to **Permissions** tab
3. Click **Add permissions** → **Create inline policy**
4. Choose **JSON** editor
5. Paste this policy:

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

6. Click **Review policy** → **Create policy**

### Step 3: Create Access Key

1. With the IAM user still open, go to **Security credentials** tab
2. Scroll to **Access keys** section
3. Click **Create access key**
4. Choose **Command Line Interface (CLI)**
5. Check the confirmation box
6. Click **Create access key**
7. **Save both the Access Key ID and Secret Access Key** (you won't see the secret again!)

### Step 4: Set GitHub Secrets and Variables

Go to your GitHub repository: **Settings** → **Secrets and variables** → **Actions**

#### Add Secrets

Click **New repository secret** and add these 2 secrets:

| Secret Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access Key ID from Step 3 |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key from Step 3 |

#### Add Variables

Click **New repository variable** and add this variable:

| Variable Name | Value |
|---|---|
| `AWS_REGION` | `us-east-1` (or your region) |

### Step 5: Test

Push a commit to `main` branch:

```bash
git commit --allow-empty -m "Test ECR workflow"
git push origin main
```

Check GitHub Actions for the workflow run.

---

## What the Workflow Does

✅ Triggers on push to `main`
✅ Builds all images with `docker compose build`
✅ Compares local image digest with ECR's latest image digest
✅ Only pushes if the image content has changed
✅ Tags pushed images with commit SHA (e.g., `abc1234`) and `latest`
✅ Skips: `qdrant`, `chromadb`, `postgres`, `rabbitmq`
✅ Creates ECR repositories automatically

## Image Repositories Created

The workflow creates ECR repositories with these names:

- `mcp-server-tcp`
- `agent-a-web`
- `cyberner-api`
- `agent-b-web`
- `autonomous-council-api`
- `agent-c-queue`
- `cybersage-ui`
- `backend`
- `frontend-react`

## Verify Setup

### Check Secrets and Variables are Set

In GitHub: **Settings** → **Secrets and variables** → **Actions**

You should see:
- ✅ AWS_ACCESS_KEY_ID (Secrets)
- ✅ AWS_SECRET_ACCESS_KEY (Secrets)
- ✅ AWS_REGION (Variables)

### Check IAM User Permissions

```bash
# List inline policies
aws iam list-user-policies --user-name github-ecr-push

# View the policy
aws iam get-user-policy --user-name github-ecr-push --policy-name <policy-name>
```

### Check Images in ECR

```bash
# List repositories
aws ecr describe-repositories --region us-east-1

# List images in a repository
aws ecr describe-images --repository-name mcp-server-tcp --region us-east-1
```

## Troubleshooting

### Access Key Error in Workflow
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets are set correctly
- Check that the secret names match exactly (case-sensitive)
- Regenerate the access key if unsure

### Permission Denied Error
- Verify the IAM user has the ECR policy attached
- Check that all permissions in the policy are included
- Try adding `ecr:*` for the Resource temporarily to test

### ECR Repository Creation Failed
- Check that the IAM user policy includes `ecr:CreateRepository`
- Ensure you have ECR quota remaining in your region

### AWS_REGION Variable Error
- Make sure AWS_REGION is added as a **Variable** (not a Secret)
- Check the spelling and case match exactly

## Security Notes

🔒 Keep your access keys private - they grant AWS access
🔒 Rotate access keys periodically
🔒 Use GitHub secret masking (automatic for secrets)
🔒 Consider using IAM policies to limit ECR-only access (as shown)

## Need More Details?

See `AWS_ECR_SETUP.md` for comprehensive setup guide with additional information and troubleshooting.
