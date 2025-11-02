# Quick Start Guide: Deploying Cybersage to EKS

## Prerequisites
- AWS account with EKS access
- kubectl configured to access your EKS cluster
- Helm 3.x installed

## 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, region (us-east-1)
```

## 2. Update kubeconfig

```bash
aws eks update-kubeconfig \
  --name cybersage-primary \
  --region us-east-1
```

## 3. Create Namespace

```bash
kubectl create namespace cybersage
```

## 4. Create Required Secrets

⚠️ **IMPORTANT**: Never commit actual secret values to git. Treat these as sensitive!

```bash
# 1. Database credentials
kubectl create secret generic postgres-credentials \
  --from-literal=password='CHANGE_ME_STRONG_PASSWORD' \
  -n cybersage

# 2. RabbitMQ credentials
kubectl create secret generic rabbitmq-credentials \
  --from-literal=password='CHANGE_ME_RABBITMQ_PASSWORD' \
  -n cybersage

# 3. Agent A Web service secrets
kubectl create secret generic agent-a-web-secrets \
  --from-literal=OPENAI_API_KEY='sk-your-actual-openai-key' \
  --from-literal=NVD_API_KEY='your-actual-nvd-api-key' \
  -n cybersage

# 4. Autonomous Council API secrets
kubectl create secret generic autonomous-council-api-secrets \
  --from-literal=OPENAI_API_KEY='sk-your-actual-openai-key' \
  --from-literal=NVD_API_KEY='your-actual-nvd-api-key' \
  --from-literal=TAVILY_API_KEY='your-actual-tavily-key' \
  --from-literal=DB_PASSWORD='CHANGE_ME_STRONG_PASSWORD' \
  --from-literal=POSTGRES_PASSWORD='CHANGE_ME_STRONG_PASSWORD' \
  -n cybersage

# 5. Backend service secrets
kubectl create secret generic backend-secrets \
  --from-literal=TAVILY_API_KEY='your-actual-tavily-key' \
  --from-literal=DB_PASSWORD='CHANGE_ME_STRONG_PASSWORD' \
  -n cybersage

# 6. MCP Server TCP secrets
kubectl create secret generic mcp-server-tcp-secrets \
  --from-literal=OPENAI_API_KEY='sk-your-actual-openai-key' \
  -n cybersage
```

**Verify secrets were created:**
```bash
kubectl get secrets -n cybersage
```

## 5. Get ECR Registry URL

```bash
ECR_REGISTRY=$(aws ecr describe-repositories \
  --query 'repositories[0].repositoryUri' \
  --output text | cut -d'/' -f1)

echo $ECR_REGISTRY
```

## 6. Deploy with Helm

```bash
helm upgrade --install cybersage ./helm/cybersage \
  --namespace cybersage \
  --values ./helm/cybersage/values.yaml \
  --set global.registry.url=$ECR_REGISTRY \
  --wait \
  --timeout 5m
```

## 7. Verify Deployment

```bash
# Check all deployments
kubectl get deployments -n cybersage

# Check all pods
kubectl get pods -n cybersage

# Check services
kubectl get services -n cybersage

# Watch pods coming up (Ctrl+C to exit)
kubectl get pods -n cybersage -w
```

## 8. View Application Logs

```bash
# View logs from a service
kubectl logs -f -l app=agent_a_web -n cybersage

# View logs from a specific pod
kubectl logs -f <pod-name> -n cybersage

# View previous logs (if pod crashed)
kubectl logs --previous <pod-name> -n cybersage
```

## Common Tasks

### Access Service Locally

```bash
# Forward localhost:8000 to autonomous-council-api:8000
kubectl port-forward svc/autonomous-council-api 8000:8000 -n cybersage

# Now access at http://localhost:8000
```

### Scale a Service

```bash
kubectl scale deployment agent_a_web --replicas=3 -n cybersage
```

### Update Environment Variables

1. Edit `deploy/helm/cybersage/values/<service-name>.yaml`
2. Reapply the Helm chart:
```bash
helm upgrade cybersage ./helm/cybersage \
  --namespace cybersage \
  --set global.registry.url=$ECR_REGISTRY
```

### Restart All Services

```bash
kubectl rollout restart deployment -n cybersage
```

### Check Service Status

```bash
kubectl get all -n cybersage
```

### Delete Everything

```bash
helm uninstall cybersage -n cybersage
kubectl delete namespace cybersage
```

## Automated Deployment (CI/CD)

Once GitHub Secrets are configured, automated deployment happens when you:

1. Push code to the `main` branch
2. `build-and-push-ecr` workflow builds and pushes images
3. `deploy-to-eks` workflow automatically deploys to EKS

No manual steps needed after the initial setup!

## Troubleshooting

### Pod Status: ImagePullBackOff
- Check ECR repository exists: `aws ecr describe-repositories`
- Verify image was pushed: `aws ecr describe-images --repository-name cybersage-primary-agent_a_web`
- Check image tag matches deployment

### Pod Status: CrashLoopBackOff
- Check logs: `kubectl logs <pod-name> -n cybersage`
- Check environment variables are set correctly
- Verify secrets exist: `kubectl get secrets -n cybersage`

### Pod Status: Pending
- Check node resources: `kubectl describe nodes`
- May need to scale node group in AWS Console
- Or adjust resource requests in `helm/cybersage/values.yaml`

### Services can't connect to each other
- Verify services are running: `kubectl get svc -n cybersage`
- Test DNS: `kubectl exec -it <pod-name> -n cybersage -- nslookup autonomous-council-api`
- Check security groups in AWS Console

For more details, see [README.md](./README.md)
