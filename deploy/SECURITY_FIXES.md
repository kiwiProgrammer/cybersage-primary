# Security Fixes - Secret Management & Kubernetes Naming Compliance

## Summary

Hardcoded API keys and sensitive data have been removed from the Helm values files and replaced with secure Kubernetes Secret references. Additionally, service names have been updated to comply with Kubernetes RFC 1123 naming requirements.

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
# Also, service names with underscores created invalid Kubernetes resource names
```

**After (FIXED):**
```yaml
# Single 'env:' with all secret keys as array items
env:
{{- range $envFile.secretKeys }}
- name: {{ . }}
  valueFrom:
    secretKeyRef:
      name: {{ $serviceName | replace "_" "-" }}-secrets
      key: {{ . }}
{{- end }}
# Results in proper YAML with single env array
# Service names with underscores are converted to hyphens for Kubernetes RFC 1123 compliance
```

**Also fixed ConfigMap naming:**
```yaml
# ConfigMap now uses the same replace filter for proper naming
metadata:
  name: {{ $serviceName | replace "_" "-" }}-config
```

### 4. Fixed Kubernetes Naming Compliance

**Problem A - RFC 1123 for Secrets/ConfigMaps:**
Service names with underscores (e.g., `agent_a_web`, `autonomous_council_api`) created invalid Kubernetes resource names when suffixed with `-secrets` or `-config` (e.g., `agent_a_web-secrets`). Kubernetes requires Secret and ConfigMap names to conform to RFC 1123.

**Error Message:**
```
The Secret "agent_a_web-secrets" is invalid: metadata.name: Invalid value:
"agent_a_web-secrets": a lowercase RFC 1123 subdomain must consist of lower
case alphanumeric characters, '-' or '.', and must start and end with an
alphanumeric character
```

**Problem B - DNS-1035 for Services/Deployments:**
Service and Deployment resource names also cannot contain underscores. They must conform to DNS-1035 labels which are even more restrictive than RFC 1123.

**Error Message:**
```
Service "agent_a_web" is invalid: metadata.name: Invalid value: "agent_a_web":
a DNS-1035 label must consist of lower case alphanumeric characters or '-',
start with an alphabetic character, and end with an alphanumeric character
(e.g. 'my-name', or 'abc-123', regex used for validation is '[a-z]([-a-z0-9]*[a-z0-9])?')
```

**Solution:** Updated all service name references to replace underscores with hyphens:
- `agent_a_web` → `agent-a-web`
- `autonomous_council_api` → `autonomous-council-api`
- `mcp_server_tcp` → `mcp-server-tcp`

This is handled automatically in the Helm templates using the `replace "_" "-"` filter on:
- Deployment names: `metadata.name: {{ $serviceName | replace "_" "-" }}`
- Service names: `metadata.name: {{ $serviceName | replace "_" "-" }}`
- Container names: `name: {{ $serviceName | replace "_" "-" }}`
- ConfigMap names: `metadata.name: {{ $serviceName | replace "_" "-" }}-config`
- Secret names: `name: {{ $serviceName | replace "_" "-" }}-secrets`

### 5. Updated Documentation

- ✅ `README.md` - Added security notice, secret creation instructions, and RFC 1123 naming note
- ✅ `QUICK_START.md` - Updated with secure secret creation
- ✅ `templates/secrets-template.yaml` - Comprehensive secret creation guide
- ✅ `ENV_VARS_REFERENCE.md` - Security considerations added
- ✅ `SECURITY_FIXES.md` - Added RFC 1123 naming compliance documentation

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
3. The deployment template merges both with proper RFC 1123 naming:
   ```yaml
   envFrom:
   - configMapRef:
       name: {{ $serviceName | replace "_" "-" }}-config

   env:
   - name: OPENAI_API_KEY
     valueFrom:
       secretKeyRef:
         name: {{ $serviceName | replace "_" "-" }}-secrets
         key: OPENAI_API_KEY
   ```

   This ensures that service names like `agent_a_web` are automatically converted to `agent-a-web` in Kubernetes resource names, maintaining RFC 1123 compliance.

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
| `templates/deployment.yaml` | Fixed YAML generation for secret env vars; Added DNS-1035 name conversion for Deployment/container names |
| `templates/service.yaml` | Added DNS-1035 name conversion for Service names |
| `templates/configmap.yaml` | Added RFC 1123 name conversion for ConfigMap names |
| `templates/secrets-template.yaml` | Added comprehensive secret creation guide |
| `.github/workflows/deploy-to-eks.yml` | Updated secret creation to use hyphenated names |
| `README.md` | Added security section, secret instructions, and naming note |
| `QUICK_START.md` | Updated with secure secret creation |
| `SECURITY_FIXES.md` | This file - detailed explanation of naming compliance |

All changes maintain backward compatibility with the Helm chart structure while improving security posture and Kubernetes resource naming compliance (DNS-1035 for Services/Deployments, RFC 1123 for Secrets/ConfigMaps).
