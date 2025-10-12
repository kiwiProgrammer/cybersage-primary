# Agent B Web - CTI JSON Processor

A RabbitMQ consumer service that processes CTI (Cyber Threat Intelligence) JSON files and ingests them into Qdrant vector database.

## Overview

Agent B Web listens to the RabbitMQ queue `data.ingest.done` and automatically processes CTI JSON files when new data ingestion events occur.

## Features

- **REST API**: FastAPI endpoints for monitoring task status and viewing results
- **Task Tracking**: In-memory storage of all task status and details
- **Background Task Processing**: Each message is processed in a separate background thread, allowing the consumer to handle multiple messages concurrently
- **Configurable Concurrency**: Control the number of concurrent workers via `MAX_WORKERS` environment variable
- **Automatic Reconnection**: Automatically reconnects to RabbitMQ on connection failures
- **Graceful Shutdown**: Waits for all background tasks to complete before shutting down
- **Thread-Safe Acknowledgment**: Uses RabbitMQ's thread-safe callback mechanism for message acknowledgment

## Processing Pipeline

When a message is received from the RabbitMQ queue:

1. **Load JSON Files**: Reads all `*.json` files from `/app/out` directory
2. **Transform Fields**: Converts `summary` field to `text` field in each JSON object
3. **Merge Data**: Combines all JSON objects into a single array
4. **Save Temporary File**: Saves merged data to `/app/pending` with timestamp
5. **Execute Chunking**: Runs `agent_b/scripts/chunk_and_ingest.py` to:
   - Chunk the text into smaller segments
   - Generate embeddings using sentence transformers
   - Ingest chunks into Qdrant vector database
6. **Cleanup**: Deletes the temporary merged file
7. **Publish Event**: Publishes completion message to RabbitMQ queue `history.graph.done`

## Architecture

```
RabbitMQ Queue (data.ingest.done)
         ↓
    Agent B Web Consumer
         ↓
    Load JSON files from /app/out
         ↓
    Transform: summary → text
         ↓
    Merge into single array
         ↓
    Save to /app/pending/merged_cti_{timestamp}.json
         ↓
    Execute chunk_and_ingest.py
         ↓
    Ingest into Qdrant Vector DB
         ↓
    Delete temporary file
         ↓
    Publish to RabbitMQ Queue (history.graph.done)
```

## API Endpoints

The service exposes a REST API for monitoring task processing:

### GET `/`
Root endpoint with API information.

**Response:**
```json
{
  "message": "Agent B Web - CTI Processor API",
  "endpoints": {
    "/tasks": "GET - List all tasks",
    "/tasks/{task_id}": "GET - Get specific task status",
    "/health": "GET - Health check",
    "/docs": "GET - API documentation"
  }
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "agent_b_cti_processor",
  "rabbitmq_connected": true,
  "total_tasks": 42
}
```

### GET `/tasks`
List all tasks with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed)
- `limit` (optional): Maximum number of tasks to return (default: 100)

**Example:**
```bash
# List all tasks
curl http://localhost:8200/tasks

# List only completed tasks
curl http://localhost:8200/tasks?status=completed

# List first 10 tasks
curl http://localhost:8200/tasks?limit=10
```

**Response:**
```json
{
  "total": 5,
  "tasks": [
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "created_at": "2025-10-12T00:00:00",
      "started_at": "2025-10-12T00:00:01",
      "completed_at": "2025-10-12T00:05:30",
      "message_data": {"task_id": "abc123", "response": {...}},
      "file_count": 10,
      "merged_file": "/app/pending/merged_cti_20251012_000000.json",
      "error": null
    },
    ...
  ]
}
```

### GET `/tasks/{task_id}`
Get detailed status and result of a specific task.

**Example:**
```bash
curl http://localhost:8200/tasks/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "task": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "created_at": "2025-10-12T00:00:00",
    "started_at": "2025-10-12T00:00:01",
    "completed_at": "2025-10-12T00:05:30",
    "message_data": {
      "task_id": "abc123",
      "timestamp": "2025-10-12T00:00:00",
      "response": {
        "success": true,
        "exit_code": 0,
        "output": "..."
      }
    },
    "file_count": 10,
    "merged_file": "/app/pending/merged_cti_20251012_000000.json",
    "error": null
  }
}
```

**Error Response (404):**
```json
{
  "detail": "Task 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

### Interactive API Documentation

Visit http://localhost:8200/docs for interactive Swagger UI documentation.

## Configuration

Environment variables:

### RabbitMQ Configuration
- `RABBITMQ_HOST` - RabbitMQ server host (default: "rabbitmq")
- `RABBITMQ_PORT` - RabbitMQ server port (default: 5672)
- `RABBITMQ_USER` - RabbitMQ username (default: "root")
- `RABBITMQ_PASS` - RabbitMQ password (default: "toor")
- `RABBITMQ_QUEUE` - Queue to consume from (default: "data.ingest.done")

### Directory Configuration
- `OUT_DIR` - Input directory for JSON files (default: "/app/out")
- `PENDING_DIR` - Output directory for merged files (default: "/app/pending")

### Qdrant Configuration
- `QDRANT_URL` - Qdrant server URL (default: "http://localhost:6333")
- `QDRANT_COLLECTION` - Collection name (default: "heva_docs")

### Performance Configuration
- `MAX_WORKERS` - Number of concurrent background workers (default: 4)

### API Configuration
- `API_PORT` - Port for FastAPI server (default: 8200)

## Running the Service

### Docker Compose (Recommended)

```bash
# Start all services including agent_b_web
docker-compose up -d agent_b_web

# View logs
docker-compose logs -f agent_b_web
```

### Standalone (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run both API and consumer (default)
python app.py

# Run API server only
python app.py --api-only

# Run consumer only (no API)
python app.py --consumer-only

# Run in test mode (process once and exit)
python app.py --test
```

### Accessing the API

Once running, access the API at:
- **API Root**: http://localhost:8200/
- **List Tasks**: http://localhost:8200/tasks
- **Task Details**: http://localhost:8200/tasks/{task_id}
- **Health Check**: http://localhost:8200/health
- **API Documentation**: http://localhost:8200/docs

## Testing

### Test Mode

Run the processor once without connecting to RabbitMQ:

```bash
python app.py --test
```

This will:
1. Process all JSON files in the OUT_DIR
2. Transform and merge them
3. Execute chunk_and_ingest
4. Exit after completion

### Manual Message Publishing

Publish a test message to trigger processing:

```python
import pika
import json

credentials = pika.PlainCredentials('root', 'toor')
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost', 5672, credentials=credentials)
)
channel = connection.channel()

message = {
    "task_id": "test-123",
    "timestamp": "2025-10-12T00:00:00",
    "response": {"success": True}
}

channel.basic_publish(
    exchange='',
    routing_key='data.ingest.done',
    body=json.dumps(message)
)

connection.close()
```

## Event Publishing

When a task completes successfully, a message is published to the RabbitMQ queue `history.graph.done` with the following format:

### Published Message Format

```json
{
  "timestamp": "2025-10-12T00:05:30.123456",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "completed_at": "2025-10-12T00:05:30",
    "file_count": 10,
    "merged_file": "/app/pending/merged_cti_20251012_000530.json",
    "collection": "heva_docs",
    "qdrant_url": "http://qdrant:6333"
  }
}
```

**Fields:**
- `timestamp`: ISO 8601 timestamp when message was published
- `task_id`: Unique task identifier (included at both levels for routing)
- `data.status`: Always "completed" (only successful tasks publish)
- `data.completed_at`: When the task finished
- `data.file_count`: Number of JSON files processed
- `data.merged_file`: Path to merged file (may be null if deleted)
- `data.collection`: Qdrant collection name where data was ingested
- `data.qdrant_url`: Qdrant server URL

This event can be consumed by downstream services (e.g., history graph builder) to trigger further processing.

## Data Format

### Input JSON Format

Expected JSON files in `/app/out`:

```json
{
  "_id": "https://example.com/report",
  "summary": "This is the threat intelligence summary text...",
  "title": "Threat Report Title",
  "published_at": "2025-10-12T00:00:00Z",
  "source_type": "blog"
}
```

### Transformed Format

After transformation:

```json
{
  "_id": "https://example.com/report",
  "text": "This is the threat intelligence summary text...",
  "title": "Threat Report Title",
  "published_at": "2025-10-12T00:00:00Z",
  "source_type": "blog"
}
```

### Merged Array Format

Saved to `/app/pending/merged_cti_{timestamp}.json`:

```json
[
  {
    "_id": "https://example.com/report1",
    "text": "First report text...",
    ...
  },
  {
    "_id": "https://example.com/report2",
    "text": "Second report text...",
    ...
  }
]
```

## Dependencies

- **pika** - RabbitMQ client
- **torch** - PyTorch for ML operations
- **sentence-transformers** - Text embedding models
- **qdrant-client** - Qdrant vector database client
- **tqdm** - Progress bars

## Error Handling

- Failed JSON file processing is logged but doesn't stop the entire process
- RabbitMQ connection errors trigger automatic reconnection (5 second retry)
- If chunk_and_ingest fails, the merged file is kept for debugging
- Messages are negatively acknowledged on processing errors (requeued)

## Monitoring

### Via API

Monitor task processing via the REST API:

```bash
# List all tasks
curl http://localhost:8200/tasks

# List running tasks
curl http://localhost:8200/tasks?status=running

# List completed tasks
curl http://localhost:8200/tasks?status=completed

# List failed tasks
curl http://localhost:8200/tasks?status=failed

# Get specific task details
curl http://localhost:8200/tasks/123e4567-e89b-12d3-a456-426614174000

# Check service health
curl http://localhost:8200/health
```

### Via Logs

Check logs for processing status:

```bash
# Docker logs
docker-compose logs -f agent_b_web

# Grep for specific events
docker-compose logs agent_b_web | grep "Processing new message"
docker-compose logs agent_b_web | grep "Task.*completed successfully"
docker-compose logs agent_b_web | grep "ERROR"

# Follow logs for a specific task
docker-compose logs -f agent_b_web | grep "Task 123e4567"
```

## Performance and Scaling

### Background Task Processing

The service uses a **ThreadPoolExecutor** to process messages concurrently:

```
RabbitMQ Message → on_message (main thread)
                   ↓
         Submit to ThreadPoolExecutor
                   ↓
    [Worker 1]  [Worker 2]  [Worker 3]  [Worker 4]
        ↓            ↓            ↓            ↓
    Process      Process      Process      Process
    Message      Message      Message      Message
        ↓            ↓            ↓            ↓
    Acknowledge  Acknowledge  Acknowledge  Acknowledge
    (thread-safe callback)
```

### Tuning Concurrency

Adjust `MAX_WORKERS` based on your workload:

- **Low concurrency (1-2 workers)**: Sequential processing, lower memory usage
  ```yaml
  environment:
    - MAX_WORKERS=1
  ```

- **Medium concurrency (4-8 workers)**: Balanced throughput and resource usage (default: 4)
  ```yaml
  environment:
    - MAX_WORKERS=4
  ```

- **High concurrency (10+ workers)**: Maximum throughput, higher memory usage
  ```yaml
  environment:
    - MAX_WORKERS=10
  ```

### Considerations

- Each worker processes one message at a time
- Memory usage increases with concurrent workers (embedding model + data)
- CPU/GPU resources are shared across workers
- Set `prefetch_count` equals `MAX_WORKERS` for optimal message distribution

## Integration

This service integrates with:
- **Agent A Web** (upstream) - Receives completion events via `data.ingest.done` queue when CTI data is ingested
- **History Graph Builder** (downstream) - Publishes completion events to `history.graph.done` queue after processing
- **RabbitMQ** - Message queue for event-driven processing (consumes from `data.ingest.done`, publishes to `history.graph.done`)
- **Qdrant** - Vector database for storing embedded text chunks
- **Shared Volume** - Accesses `/app/out` volume created by agent_a_web

### Message Flow

```
Agent A Web → [data.ingest.done] → Agent B Web → [history.graph.done] → Next Service
```

## Troubleshooting

### Service won't start
- Check RabbitMQ is running: `docker-compose ps rabbitmq`
- Check Qdrant is running: `docker-compose ps qdrant`
- Verify environment variables are set correctly

### No files being processed
- Check files exist in `/app/out`: `docker-compose exec agent_b_web ls -la /app/out`
- Verify RabbitMQ queue has messages: Check management UI at http://localhost:15672

### Qdrant ingestion fails
- Verify Qdrant is accessible: `curl http://localhost:6333/collections`
- Check Qdrant logs: `docker-compose logs qdrant`
- Ensure sufficient memory for embedding model

### Memory issues
- Reduce `--batch-chunks` parameter in chunk_and_ingest execution
- Reduce `--encode-batch-size` for smaller GPU/CPU memory
- Use CPU-only mode if GPU memory is insufficient

## Development

### Adding Custom Transformations

Edit the `transform_summary_to_text()` function in `app.py`:

```python
def transform_summary_to_text(data: Dict[str, Any]) -> Dict[str, Any]:
    # Add your custom transformations here
    if "summary" in data:
        data["text"] = data.pop("summary")

    # Example: Add custom field
    data["processed_by"] = "agent_b_web"
    data["processed_at"] = datetime.now().isoformat()

    return data
```

### Extending Processing Logic

The `process_message()` function can be extended with additional steps:

```python
def process_message(message_data: Dict[str, Any]):
    # Existing steps...

    # Add custom step
    logger.info("Custom step: Performing additional analysis")
    perform_custom_analysis(transformed_data)

    # Continue with existing steps...
```
