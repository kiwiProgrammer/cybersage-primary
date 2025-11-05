# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used by Cybersage services.

## agent-a-web

Location: `helm/cybersage/values/agent-a-web.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| DATABASE_URL | string | `sqlite:///app/data` | SQLite database path |
| KEV_CACHE_URL | string | `https://www.cisa.gov/...` | CISA known exploited vulnerabilities feed URL |
| LLM_CVE_MAX_TOKENS | number | `2000` | Maximum tokens for CVE analysis |
| LLM_CYBER_MAX_TOKENS | number | `5500` | Maximum tokens for cyber analysis |
| LLM_DEFAULT_MAX_TOKENS | number | `5500` | Default maximum tokens |
| LLM_ENTITY_MAX_TOKENS | number | `5000` | Maximum tokens for entity extraction |
| LLM_GEO_MOTIVATION_MAX_TOKENS | number | `5000` | Maximum tokens for geo/motivation |
| LLM_IOC_MAX_TOKENS | number | `5000` | Maximum tokens for IOC analysis |
| LLM_MITRE_MAX_TOKENS | number | `8000` | Maximum tokens for MITRE ATT&CK |
| LLM_OVERLAP_TOKENS | number | `200` | Token overlap for context |
| LLM_SUMMARIZE_MAX_TOKENS | number | `5000` | Maximum tokens for summarization |
| LLM_SUMMARY_MAX_TOKENS | number | `7000` | Maximum tokens for summary |
| LOG_LEVEL | string | `INFO` | Logging level (INFO, DEBUG, WARNING) |
| MAX_CONTENT_BYTES | number | `5000000` | Maximum content size in bytes |
| MAX_RETRIES | number | `3` | Maximum retry attempts |
| MITRE_ATTACK_URL | string | MITRE ATT&CK URL | MITRE ATT&CK framework URL |
| NVD_API_KEY | string | *(secret)* | NVD API key |
| OPENAI_API_KEY | string | *(secret)* | OpenAI API key |
| OPENAI_MODEL | string | `gpt-4o-mini` | OpenAI model name |
| OUTPUT_DIR | string | `/app/out` | Output directory |
| RETRY_DELAY | number | `10.0` | Retry delay in seconds |
| S3_BUCKET | string | `` | S3 bucket name (optional) |
| S3_REGION | string | `ap-southeast-1` | AWS region for S3 |
| TIMEOUT_SECONDS | number | `20` | Request timeout in seconds |

### Dependencies
- rabbitmq
- postgres

## agent-b-web

Location: `helm/cybersage/values/agent-b-web.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| API_PORT | number | `8200` | API listening port |
| MAX_WORKERS | number | `4` | Maximum concurrent workers |
| OUT_DIR | string | `/app/out` | Output directory |
| PENDING_DIR | string | `/app/pending` | Pending jobs directory |
| QDRANT_COLLECTION | string | `heva_docs` | Qdrant collection name |
| QDRANT_URL | string | `http://qdrant:6333` | Qdrant service URL |
| RABBITMQ_HOST | string | `rabbitmq` | RabbitMQ host |
| RABBITMQ_PASS | string | `toor` | RabbitMQ password |
| RABBITMQ_PORT | number | `5672` | RabbitMQ port |
| RABBITMQ_QUEUE | string | `data.ingest.done` | RabbitMQ queue name |
| RABBITMQ_USER | string | `root` | RabbitMQ user |

### Dependencies
- rabbitmq
- qdrant

## agent-c-queue

Location: `helm/cybersage/values/agent-c-queue.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| AGENT_C_URL | string | `http://autonomous-council-api:8000` | Autonomous Council API URL |
| API_PORT | number | `8300` | API listening port |
| OUT_DIR | string | `/app/out` | Output directory |
| RABBITMQ_HOST | string | `rabbitmq` | RabbitMQ host |
| RABBITMQ_PASS | string | `toor` | RabbitMQ password |
| RABBITMQ_PORT | number | `5672` | RabbitMQ port |
| RABBITMQ_QUEUE | string | `history.graph.done` | RabbitMQ queue name |
| RABBITMQ_USER | string | `root` | RabbitMQ user |
| TEMP_DIR | string | `/app/temp` | Temporary directory |

### Dependencies
- rabbitmq
- autonomous-council-api

## autonomous-council-api

Location: `helm/cybersage/values/autonomous-council-api.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| CHROMA_HOST | string | `chromadb` | ChromaDB host |
| CHROMA_PORT | number | `8000` | ChromaDB port |
| DATABASE_URL | string | `sqlite:///app/data` | SQLite database path |
| DB_HOST | string | `postgres` | PostgreSQL host |
| DB_NAME | string | `postgresdb` | PostgreSQL database name |
| DB_PASSWORD | string | *(secret)* | PostgreSQL password |
| DB_PORT | number | `5432` | PostgreSQL port |
| DB_USER | string | `postgres` | PostgreSQL user |
| EMBEDDING_MODEL | string | `all-MiniLM-L6-v2` | Embedding model name |
| EXPERTISE_DB_NAME | string | `expertise_db` | Expertise database name |
| INCIDENT_DB_NAME | string | `incident_db` | Incident database name |
| KEV_CACHE_URL | string | CISA feed URL | Known exploited vulnerabilities |
| LLM_* | various | See agent-a-web | LLM token limits |
| LOG_LEVEL | string | `INFO` | Logging level |
| MAX_CONTENT_BYTES | number | `5000000` | Maximum content size |
| MAX_RETRIES | number | `3` | Maximum retry attempts |
| MCP_HOST | string | `127.0.0.1` | MCP server host |
| MCP_PORT | number | `8765` | MCP server port |
| MCP_START_SERVER | boolean | `false` | Start MCP server |
| MCP_TRANSPORT | string | `tcp` | MCP transport type |
| MODEL_PATH | string | `/app/models` | Model files path |
| NVD_API_KEY | string | *(secret)* | NVD API key |
| OLLAMA_BASE_URL | string | `http://localhost:11434` | Ollama API URL |
| OPENAI_API_KEY | string | *(secret)* | OpenAI API key |
| OPENAI_MODEL | string | `gpt-4o-mini` | OpenAI model name |
| OUTPUT_DIR | string | `/app/out` | Output directory |
| POSTGRES_* | various | | PostgreSQL settings |
| QDRANT_COLLECTION | string | `heva_docs` | Qdrant collection |
| QDRANT_URL | string | `http://qdrant:6333` | Qdrant service URL |
| REACT_APP_API_URL | string | `http://localhost:8000` | Frontend API URL |
| REACT_APP_WS_URL | string | `localhost:8000` | WebSocket URL |
| RETRY_DELAY | number | `10.0` | Retry delay seconds |
| S3_BUCKET | string | `` | S3 bucket (optional) |
| S3_REGION | string | `ap-southeast-1` | AWS region |
| SSH_TUNNEL_ENABLED | boolean | `false` | Enable SSH tunnel |
| SSH_TUNNEL_* | various | | SSH tunnel config |
| TAVILY_API_KEY | string | *(secret)* | Tavily API key |
| TIMEOUT_SECONDS | number | `20` | Request timeout |
| VECTORS_SIZE | number | `384` | Vector embedding size |

### Dependencies
- postgres
- chromadb
- qdrant

## backend

Location: `helm/cybersage/values/backend.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| DB_HOST | string | `postgres` | PostgreSQL host |
| DB_NAME | string | `postgresdb` | PostgreSQL database |
| DB_PASSWORD | string | *(secret)* | PostgreSQL password |
| DB_PORT | number | `5432` | PostgreSQL port |
| DB_USER | string | `postgres` | PostgreSQL user |
| SSH_TUNNEL_ENABLED | boolean | `false` | Enable SSH tunnel |
| SSH_TUNNEL_* | various | | SSH tunnel configuration |
| TAVILY_API_KEY | string | *(secret)* | Tavily API key |

### Dependencies
- postgres

## cybersage-ui

Location: `helm/cybersage/values/cybersage-ui.yaml`

No required environment variables. Configuration is typically build-time.

### Dependencies
- agent-a-web
- agent-b-web
- agent-c-queue

## cyberner-api

Location: `helm/cybersage/values/cyberner-api.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| QDRANT_COLLECTION | string | `heva_docs` | Qdrant collection name |
| QDRANT_URL | string | `http://qdrant:6333` | Qdrant service URL |

### Dependencies
- qdrant

## frontend-react

Location: `helm/cybersage/values/frontend-react.yaml`

No required environment variables. Configuration is typically build-time.

### Dependencies
- backend

## mcp-server-tcp

Location: `helm/cybersage/values/mcp-server-tcp.yaml`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| DATABASE_URL | string | `sqlite:////app/data/cti.db` | SQLite database path |
| LLM_MODEL | string | `gpt-4o-mini` | LLM model name |
| OPENAI_API_KEY | string | *(secret)* | OpenAI API key |
| OUTPUT_DIR | string | `/app/out` | Output directory |

## Managed Services

### PostgreSQL
- Image: `postgres:15`
- Port: 5432
- Default User: `postgres`
- Default Database: `postgresdb`
- Password: From `postgres-credentials` secret

### RabbitMQ
- Image: `rabbitmq:3-management`
- AMQP Port: 5672
- Management Port: 15672
- Default User: `root`
- Default Password: From `rabbitmq-credentials` secret

### Qdrant
- Image: `qdrant/qdrant:latest`
- gRPC Port: 6333
- HTTP Port: 6334

### ChromaDB
- Image: `chromadb/chroma:latest`
- HTTP Port: 8000
- Persistent: Yes (default)

## Updating Environment Variables

### For Non-Sensitive Variables

Edit the respective service YAML file in `helm/cybersage/values/`:

```yaml
env:
  LOG_LEVEL: "DEBUG"
  MAX_WORKERS: "8"
```

Then redeploy:
```bash
helm upgrade cybersage ./helm/cybersage -n cybersage
```

### For Sensitive Variables

Update GitHub Secrets and the deployment workflow will automatically inject them into the cluster secrets.

To manually update secrets:
```bash
kubectl create secret generic <service>-secrets \
  --from-literal=KEY=value \
  --dry-run=client -o yaml | kubectl apply -f -
```

Then restart the service:
```bash
kubectl rollout restart deployment/<service-name> -n cybersage
```

## Security Considerations

1. **Never commit secrets** to version control
2. **Use AWS Secrets Manager** for production environments
3. **Rotate API keys** regularly
4. **Use strong passwords** for database credentials
5. **Enable audit logging** for sensitive operations
6. **Restrict** environment variable access via RBAC

## Troubleshooting

### Service not connecting to dependency

Check environment variables are set correctly:
```bash
kubectl exec <pod-name> -n cybersage -- env | grep -i <service_name>
```

### API key issues

Verify secrets are created:
```bash
kubectl get secrets -n cybersage
kubectl describe secret <secret-name> -n cybersage
```

### Database connection errors

Test PostgreSQL connectivity:
```bash
kubectl exec <pod-name> -n cybersage -- \
  psql -h postgres -U postgres -d postgresdb
```
