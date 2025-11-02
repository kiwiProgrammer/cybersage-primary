# Security Fixes - Secret Management

## Summary

Hardcoded API keys and sensitive data have been removed from the Helm values files and replaced with secure Kubernetes Secret references.

## What Was Fixed

### 1. Removed Hardcoded API Keys

Previously, sensitive data was stored in plain text in values files:

**Before (INSECURE):**
```yaml
# deploy/helm/cybersage/values/agent_a_web.yaml
env:
  NVD_API_KEY: "1c2c7de7-0340-49eb-8343-40df36a6d223"
  OPENAI_API_KEY: "sk-proj-3No4WjfFulhlP1ZCJ5zEVOMk7Xc3MvW7b0Te-N9zVd7AJy1_BntWb0_..."
```

**After (SECURE):**
```yaml
# These values are now injected from Kubernetes Secrets
env:
  # Regular variables only - no sensitive data
  MITRE_ATTACK_URL: "https://..."

secretKeys:
  - OPENAI_API_KEY
  - NVD_API_KEY
```

### 2. Updated Services

The following service configuration files have been updated to remove hardcoded secrets:

- ✅ `values/agent_a_web.yaml` - Removed NVD_API_KEY, OPENAI_API_KEY
- ✅ `values/autonomous_council_api.yaml` - Removed NVD_API_KEY, hardcoded passwords
- ✅ `values/backend.yaml` - Removed hardcoded passwords
- ✅ `values/mcp_server_tcp.yaml` - Already using secrets
- ✅ All other service files cleaned

### 3. Fixed Deployment Template

**Before (BROKEN):**
```yaml
# deployment.yaml had multiple 'env:' declarations in a loop
# This created invalid YAML
{{- range $envFile.secretKeys }}
env:
- name: {{ . }}
  ...
{{- end }}
# Results in: env: ... env: ... env: ... (multiple declarations!)
```

**After (FIXED):**
```yaml
# Single 'env:' with all secret keys as array items
env:
{{- range $envFile.secretKeys }}
- name: {{ . }}
  valueFrom:
    secretKeyRef:
      name: {{ $serviceName }}-secrets
      key: {{ . }}
{{- end }}
# Results in proper YAML with single env array
```

### 4. Updated Documentation

- ✅ `README.md` - Added security notice and secret creation instructions
- ✅ `QUICK_START.md` - Updated with secure secret creation
- ✅ `templates/secrets-template.yaml` - Comprehensive secret creation guide
- ✅ `ENV_VARS_REFERENCE.md` - Security considerations added

## Required Secrets

Before deploying the Helm chart, create these secrets:

### Database Secrets
```bash
kubectl create secret generic postgres-credentials \
  --from-literal=password='strong-password' \
  -n cybersage

kubectl create secret generic rabbitmq-credentials \
  --from-literal=password='strong-password' \
  -n cybersage
```

### Service Secrets

**agent-a-web-secrets:**
- OPENAI_API_KEY
- NVD_API_KEY

**autonomous-council-api-secrets:**
- OPENAI_API_KEY
- NVD_API_KEY
- TAVILY_API_KEY
- DB_PASSWORD
- POSTGRES_PASSWORD

**backend-secrets:**
- TAVILY_API_KEY
- DB_PASSWORD

**mcp-server-tcp-secrets:**
- OPENAI_API_KEY

See `helm/cybersage/templates/secrets-template.yaml` for complete instructions.

## How Secrets Are Now Injected

1. **Non-sensitive values** are in ConfigMaps (from `env:` in values files)
2. **Sensitive values** are in Kubernetes Secrets (from `secretKeys:` in values files)
3. The deployment template merges both:
   ```yaml
   envFrom:
   - configMapRef:
       name: {{ $serviceName }}-config

   env:
   - name: OPENAI_API_KEY
     valueFrom:
       secretKeyRef:
         name: {{ $serviceName }}-secrets
         key: OPENAI_API_KEY
   ```

## Best Practices Implemented

✅ **Never store secrets in version control**
- All hardcoded values removed
- Values files contain only non-sensitive defaults

✅ **Separate secret management**
- Use Kubernetes Secrets for sensitive data
- Use ConfigMaps for configuration

✅ **Support for AWS Secrets Manager**
- The workflow can be updated to pull from AWS Secrets Manager
- Use ExternalSecrets operator for automation

✅ **Template validation**
- Fixed YAML generation issues
- Proper handling of multiple secret keys

✅ **Documentation**
- Clear instructions for creating secrets
- Security warnings in README

## Migration Guide

If you've already deployed using the old values files:

1. **Create new secrets** (as shown above)
2. **Update deployment** with new values:
   ```bash
   helm upgrade cybersage ./helm/cybersage \
     --namespace cybersage \
     -f helm/cybersage/values.yaml
   ```
3. **Verify pods** have restarted with new secret values:
   ```bash
   kubectl get pods -n cybersage
   ```

## Future Improvements

### Option 1: AWS Secrets Manager Integration
```bash
# Install external-secrets operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets

# Create SecretStore pointing to AWS Secrets Manager
# Automatic sync of secrets from AWS to K8s
```

### Option 2: Sealed Secrets
```bash
# Use sealed-secrets for GitOps-friendly secret management
# Encrypt secrets in Git, decrypt in cluster only
```

### Option 3: HashiCorp Vault
```bash
# Use Vault for centralized secret management
# Integrate with Kubernetes auth method
```

## Verification

To verify secrets are properly created:

```bash
# List all secrets
kubectl get secrets -n cybersage

# Check a specific secret
kubectl describe secret agent-a-web-secrets -n cybersage

# Verify pod has the right environment variables
kubectl exec -it <pod-name> -n cybersage -- env | grep OPENAI_API_KEY
```

## Summary of Changes

| File | Change |
|------|--------|
| `values/agent_a_web.yaml` | Removed hardcoded API keys, added to secretKeys |
| `values/autonomous_council_api.yaml` | Removed hardcoded API keys and passwords |
| `values/backend.yaml` | Removed hardcoded passwords |
| `templates/deployment.yaml` | Fixed YAML generation for secret env vars |
| `templates/secrets-template.yaml` | Added comprehensive secret creation guide |
| `README.md` | Added security section and secret instructions |
| `QUICK_START.md` | Updated with secure secret creation |
| `SECURITY_FIXES.md` | This file - detailed explanation |

All changes maintain backward compatibility with the Helm chart structure while improving security posture.
