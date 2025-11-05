# Cybersage Kubernetes Deployment Guide

This directory contains Helm charts for deploying Cybersage services to Amazon EKS (Elastic Kubernetes Service).

## Overview

The deployment consists of:
- **Custom Services**: 9 application services built from Docker images (pulled from ECR)
- **Managed Services**: 4 backing services (PostgreSQL, RabbitMQ, Qdrant, ChromaDB)
- **Helm Chart**: Unified configuration and deployment templates

## ⚠️ SECURITY NOTICE

**API Keys and Sensitive Data**: All sensitive information (API keys, passwords) have been removed from the Helm values files and must be stored in Kubernetes Secrets. Never commit secrets to version control!

The following services require secrets to be created before deployment:
- `agent-a-web-secrets` (OPENAI_API_KEY, NVD_API_KEY)
- `autonomous-council-api-secrets` (OPENAI_API_KEY, NVD_API_KEY, TAVILY_API_KEY, DB_PASSWORD, POSTGRES_PASSWORD)
- `backend-secrets` (TAVILY_API_KEY, DB_PASSWORD)
- `mcp-server-tcp-secrets` (OPENAI_API_KEY)
- `postgres-credentials` (password)
- `rabbitmq-credentials` (password)

See [Creating Secrets](#creating-secrets-in-cluster) section for instructions.

## Prerequisites

### Local Development Requirements

1. **Helm 3.x** - Package manager for Kubernetes
   ```bash
   brew install helm  # macOS
   ```

2. **kubectl** - Kubernetes command-line tool
   ```bash
   brew install kubectl  # macOS
   ```

3. **AWS CLI v2** - For AWS operations
   ```bash
   brew install awscliv2  # macOS
   ```

### AWS Account Requirements

You'll need an AWS account with permissions to:
- Create and manage EKS clusters
- Create EC2 instances
- Create VPCs and subnets
- Create IAM roles and policies
- Access ECR repositories

## Manual AWS Setup Steps

### Step 1: Create VPC and Subnets

1. Go to **VPC Dashboard** in AWS Console
2. Click **Create VPC**
3. Configure:
   - Name: `cybersage-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - Tenancy: Default
4. Create subnets in multiple availability zones (AZs):
   - **Public Subnet 1**: `10.0.1.0/24` (AZ-a)
   - **Public Subnet 2**: `10.0.2.0/24` (AZ-b)
   - **Private Subnet 1**: `10.0.10.0/24` (AZ-a)
   - **Private Subnet 2**: `10.0.11.0/24` (AZ-b)

5. Attach **Internet Gateway** to VPC

6. Configure **Route Tables**:
   - Public route table: Route traffic (0.0.0.0/0) to Internet Gateway
   - Private route table: Route traffic (0.0.0.0/0) to NAT Gateway (optional for production)

### Step 2: Create IAM Role for EKS Cluster

1. Go to **IAM Console** → **Roles**
2. Click **Create Role**
3. Select **AWS Service** → **EKS** → **EKS - Cluster**
4. Attach policies:
   - `AmazonEKSClusterPolicy`
   - `AmazonEKSServicePolicy` (or use `AmazonEKSClusterPolicy` which includes it)
5. Name the role: `cybersage-eks-cluster-role`

### Step 3: Create IAM Role for EKS Node Group

1. Go to **IAM Console** → **Roles**
2. Click **Create Role**
3. Select **AWS Service** → **EC2** → **EC2** as use case
4. Attach policies:
   - `AmazonEKSWorkerNodePolicy`
   - `AmazonEKS_CNI_Policy`
   - `AmazonEC2ContainerRegistryReadOnly`
5. Name the role: `cybersage-eks-node-role`

### Step 4: Create EKS Cluster

1. Go to **EKS Console** → **Clusters**
2. Click **Create Cluster**
3. Configure:
   - **Cluster name**: `cybersage-primary`
   - **Kubernetes version**: Latest stable (e.g., 1.28)
   - **Cluster service role**: `cybersage-eks-cluster-role`
   - **Subnets**: Select your public and private subnets (both AZs)
   - **Security group**: Create new or select existing
   - **Cluster logging**: Enable CloudWatch logs (optional)
4. Click **Create** and wait 10-15 minutes for cluster to be active

### Step 5: Create Node Group

1. In EKS Cluster details, go to **Compute** → **Node Groups**
2. Click **Add Node Group**
3. Configure:
   - **Node group name**: `cybersage-primary-nodes`
   - **Node IAM role**: `cybersage-eks-node-role`
   - **Subnets**: Select private subnets (both AZs)
   - **Instance types**: `t3.xlarge` (recommended for Cybersage workloads)
   - **Desired size**: 2-3 nodes
   - **Min size**: 2
   - **Max size**: 5
4. Click **Create**

### Step 6: Configure kubectl Access

```bash
# Update kubeconfig to access your EKS cluster
aws eks update-kubeconfig \
  --name cybersage-primary \
  --region us-east-1  # Replace with your region

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Step 7: Create Kubernetes Namespace

```bash
kubectl create namespace cybersage
```

### Step 8: Create Storage Class (EBS)

```bash
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp2
provisioner: ebs.csi.aws.com
parameters:
  type: gp2
  iops: "100"
  throughput: "125"
allowVolumeExpansion: true
EOF
```

### Step 9: Install AWS EBS CSI Driver (for persistent volumes)

```bash
# Add the aws-ebs-csi-driver Helm repository
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm repo update

# Install the driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set serviceAccount.controller.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/AmazonEKS_EBS_CSI_DriverRole \
  --set enableVolumeModifications=true
```

Note: You may need to create an IAM role for the EBS CSI Driver.

### Step 10: Create ECR Repositories (if not already created)

The build workflow creates these automatically, but you can manually create them:

```bash
for service in agent-a-web agent-b-web agent-c-queue autonomous-council-api backend cybersage-ui cyberner-api frontend-react mcp-server-tcp; do
  aws ecr create-repository \
    --repository-name cybersage-primary-${service} \
    --region us-east-1  # Replace with your region
done
```

Note: Service names are automatically converted from underscores to hyphens (e.g., `agent-a-web` → `agent-a-web`) to comply with Kubernetes DNS-1035 naming requirements for resource names (Services, Deployments, containers).

## GitHub Actions Secrets Configuration

Add the following secrets to your GitHub repository (Settings → Secrets):

### AWS Credentials
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_REGION`: AWS region (e.g., `us-east-1`)
- `EKS_CLUSTER_NAME`: `cybersage-primary`

### Database Credentials
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `RABBITMQ_PASSWORD`: Password for RabbitMQ (default is `toor`)

### API Keys (from docker-compose.yml)
- `OPENAI_API_KEY`: Your OpenAI API key
- `NVD_API_KEY`: NVD API key for vulnerability data
- `TAVILY_API_KEY`: Tavily API key for research

### SSH Keys (if needed)
- `SSH_PRIVATE_KEY`: SSH private key for submodule access

## Environment Variable Management

Each service has its own environment configuration file:

```
deploy/helm/cybersage/values/
├── agent-a-web.yaml
├── agent-b-web.yaml
├── agent-c-queue.yaml
├── autonomous-council-api.yaml
├── backend.yaml
├── cybersage-ui.yaml
├── cyberner-api.yaml
├── frontend-react.yaml
└── mcp-server-tcp.yaml
```

### Updating Environment Variables

1. **Non-sensitive variables**: Edit the service's YAML file in `values/`
   ```yaml
   env:
     LOG_LEVEL: "DEBUG"  # Change as needed
     MAX_WORKERS: "4"
   ```

2. **Sensitive variables**: Update GitHub secrets and the deployment will use them

3. **Re-deploy**:
   ```bash
   helm upgrade cybersage ./helm/cybersage \
     --namespace cybersage \
     -f ./helm/cybersage/values.yaml
   ```

## Helm Chart Structure

```
deploy/helm/cybersage/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values for all services
├── values/                 # Environment-specific overrides
│   ├── agent-a-web.yaml
│   ├── agent-b-web.yaml
│   └── ... (one per service)
└── templates/
    ├── deployment.yaml     # Creates deployments for all services
    ├── service.yaml        # Creates services
    ├── configmap.yaml      # Creates ConfigMaps for env vars
    ├── managed-services.yaml # Deployments for postgres, rabbitmq, etc.
    ├── pvc.yaml            # PersistentVolumeClaims
    └── secrets-template.yaml # Guide for creating secrets
```

## Deployment Workflow

The deployment is automated via GitHub Actions:

1. **Push to `main` branch**
2. **`build-and-push-ecr.yml` workflow**:
   - Builds all services as Docker images
   - Pushes images to ECR with commit SHA tag
3. **`deploy-to-eks.yml` workflow** (triggered on success):
   - Creates secrets in the cluster
   - Deploys/updates Helm release with new image tags
   - Verifies deployment health

## Creating Secrets in Cluster

Before deploying, create all required secrets. See `helm/cybersage/templates/secrets-template.yaml` for the complete list of secrets needed.

### Quick Secret Creation

```bash
# Database credentials
kubectl create secret generic postgres-credentials \
  --from-literal=password='your-strong-password' \
  -n cybersage

kubectl create secret generic rabbitmq-credentials \
  --from-literal=password='your-rabbitmq-password' \
  -n cybersage

# Service API keys
kubectl create secret generic agent-a-web-secrets \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=NVD_API_KEY='...' \
  -n cybersage

kubectl create secret generic autonomous-council-api-secrets \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=NVD_API_KEY='...' \
  --from-literal=TAVILY_API_KEY='...' \
  --from-literal=DB_PASSWORD='your-strong-password' \
  --from-literal=POSTGRES_PASSWORD='your-strong-password' \
  -n cybersage

kubectl create secret generic backend-secrets \
  --from-literal=TAVILY_API_KEY='...' \
  --from-literal=DB_PASSWORD='your-strong-password' \
  -n cybersage

kubectl create secret generic mcp-server-tcp-secrets \
  --from-literal=OPENAI_API_KEY='sk-...' \
  -n cybersage
```

### Verify Secrets

```bash
kubectl get secrets -n cybersage
kubectl describe secret <secret-name> -n cybersage
```

## Manual Deployment

To manually deploy the Helm chart:

```bash
# 1. Create secrets first (see "Creating Secrets in Cluster" section above)

# 2. Get your ECR registry URL
ECR_REGISTRY=$(aws ecr describe-repositories \
  --query 'repositories[0].repositoryUri' \
  --output text | cut -d'/' -f1)

# 3. Deploy with Helm
helm upgrade --install cybersage ./helm/cybersage \
  --namespace cybersage \
  --values ./helm/cybersage/values.yaml \
  --set global.registry.url=$ECR_REGISTRY \
  --wait

# 4. Check deployment status
kubectl get deployments -n cybersage
kubectl get pods -n cybersage
kubectl get services -n cybersage
```

## Scaling Services

To scale a specific service:

```bash
# Scale agent-a-web to 3 replicas
kubectl scale deployment agent-a-web --replicas=3 -n cybersage

# Or update values and redeploy
helm upgrade cybersage ./helm/cybersage \
  --set "services.agent-a-web.replicas=3" \
  -n cybersage
```

## Monitoring and Debugging

### View Logs

```bash
# View logs from a specific pod
kubectl logs -f <pod-name> -n cybersage

# View logs from all pods of a service
kubectl logs -f -l app=agent-a-web -n cybersage
```

### Check Pod Status

```bash
# Get detailed pod information
kubectl describe pod <pod-name> -n cybersage

# Get all pods and their status
kubectl get pods -n cybersage -o wide

# Watch pods in real-time
kubectl get pods -n cybersage -w
```

### Port Forwarding (for testing)

```bash
# Forward local port 8000 to service port 8000
kubectl port-forward svc/autonomous-council-api 8000:8000 -n cybersage

# Forward to a specific pod
kubectl port-forward pod/<pod-name> 8000:8000 -n cybersage
```

## Persistence and Data

Each managed service uses EBS-backed PersistentVolumes:

- **PostgreSQL**: `postgres-pvc` (10Gi by default)
- **RabbitMQ**: `rabbitmq-pvc` (5Gi by default)
- **Qdrant**: `qdrant-pvc` (20Gi by default)
- **ChromaDB**: `chromadb-pvc` (10Gi by default)

To increase storage:

```bash
# Edit the PVC
kubectl edit pvc postgres-pvc -n cybersage

# Change `spec.resources.requests.storage` to desired size
```

## Cost Optimization

1. **Use Spot Instances** for non-critical node groups (saves ~70%)
2. **Auto-scale** node groups based on resource usage
3. **Use Horizontal Pod Autoscaler** for services that need scaling
4. **Consider using smaller instances** for development (t3.large instead of t3.xlarge)

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n cybersage

# Common issues:
# - Image not found: Verify ECR registry URL and image tags
# - Insufficient resources: Check node capacity
# - Secrets missing: Verify secrets are created
```

### Images not pulling from ECR

```bash
# Verify ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Check image tags
aws ecr describe-images --repository-name cybersage-primary-agent-a-web --region us-east-1
```

### Service connectivity issues

```bash
# Test connectivity between pods
kubectl exec -it <pod-name> -n cybersage -- bash
# Inside pod:
curl http://autonomous-council-api:8000/
```

## Cleanup

To remove the entire deployment:

```bash
# Delete the Helm release
helm uninstall cybersage -n cybersage

# Delete the namespace
kubectl delete namespace cybersage
```

To delete AWS resources:

```bash
# Delete node group
aws eks delete-nodegroup --cluster-name cybersage-primary --nodegroup-name cybersage-primary-nodes

# Delete cluster (wait for node group to finish deleting first)
aws eks delete-cluster --name cybersage-primary

# Delete VPC (requires deleting all associated resources first)
# Done via AWS Console: VPC → Delete
```

## Next Steps

1. Complete all manual AWS setup steps above
2. Add GitHub secrets to your repository
3. Push to `main` branch to trigger the automated deployment workflow
4. Monitor the GitHub Actions workflow for build and deployment status
5. Verify pods are running: `kubectl get pods -n cybersage`
6. Access services via port-forward or Ingress (if configured)

## Support and Maintenance

For issues or questions:
1. Check Kubernetes events: `kubectl get events -n cybersage`
2. Review pod logs: `kubectl logs <pod-name> -n cybersage`
3. Check AWS CloudWatch logs for cluster events
4. Verify GitHub Actions workflow logs for deployment issues
