# Agent A Web API

FastAPI web interface for the Agent A CTI pipeline.

## Overview

This service provides a REST API that executes the `agent_a` CLI tool asynchronously. Submit URLs for processing and check status/results via task ID.

## Installation

### Local Installation

```bash
pip install -r requirements.txt
```

### Docker Installation

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t agent_a_web -f Dockerfile ..
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key agent_a_web
```

## Running the Server

### Local

```bash
# From the agent_a_web directory
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f agent_a_web

# Stop the service
docker-compose down
```

The server will start on `http://0.0.0.0:8000`

## Environment Variables

Create a `.env` file or set these environment variables:

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
LLM_MODEL=gpt-4o-mini
OUTPUT_DIR=./out
LOG_LEVEL=INFO
```

## API Endpoints

### GET /
Root endpoint with basic service information and available endpoints.

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "agent_a_cti_pipeline"
}
```

### POST /run (Async Task Submission)
Submit the agent_a CLI run command for asynchronous execution.

This endpoint submits a task and returns immediately with a `task_id`. The CLI command runs in the background, and you can check its status using the `/task/{task_id}` endpoint.

**Request Body:**
```json
{
  "urls": ["https://example.com/report"],
  "output_dir": "./out",
  "auth_username": null,
  "auth_password": null,
  "no_ssl_verify": false,
  "bypass_memory": false,
  "log_level": "INFO"
}
```

**Parameters:**
- `urls` (required): List of URLs to process (minimum 1)
- `output_dir` (optional): Output directory for artifacts (default: "./out")
- `auth_username` (optional): Username for HTTP basic authentication
- `auth_password` (optional): Password for HTTP basic authentication
- `no_ssl_verify` (optional): Disable SSL certificate verification (default: false)
- `bypass_memory` (optional): Bypass memory check and reprocess URLs (default: false)
- `log_level` (optional): Log level - DEBUG, INFO, WARNING, ERROR (default: "INFO")

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Task submitted successfully. Use /task/{task_id} to check status."
}
```

### GET /task/{task_id} (Check Task Status)
Retrieve the status and results of a submitted task.

**Response (Pending/Running):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "submitted_at": "2025-10-11T20:30:00",
  "started_at": "2025-10-11T20:30:01",
  "completed_at": null,
  "result": null
}
```

**Response (Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "submitted_at": "2025-10-11T20:30:00",
  "started_at": "2025-10-11T20:30:01",
  "completed_at": "2025-10-11T20:35:00",
  "result": {
    "success": true,
    "exit_code": 0,
    "output": "Processing complete: 1/1 successful...",
    "error": null
  }
}
```

**Status Values:**
- `pending`: Task queued, waiting to start
- `running`: Task is currently executing
- `completed`: Task finished successfully
- `failed`: Task encountered an error

## Usage Examples

### Using curl

```bash
# Submit a task to process URLs
TASK_RESPONSE=$(curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.cisa.gov/news-events/alerts/2024/01/15/example"]
  }')

# Extract task_id from response
TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "Task ID: $TASK_ID"

# Check task status
curl "http://localhost:8000/task/$TASK_ID"

# Process multiple URLs with custom settings
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/report1",
      "https://example.com/report2"
    ],
    "output_dir": "/app/out",
    "bypass_memory": false,
    "log_level": "DEBUG"
  }'

# Process with HTTP authentication
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://protected.example.com/report"],
    "auth_username": "user",
    "auth_password": "pass"
  }'
```

### Using Python requests

```python
import requests
import time

# Submit task
submit_url = "http://localhost:8000/run"
payload = {
    "urls": ["https://www.cisa.gov/news-events/alerts/2024/01/15/example"],
    "output_dir": "./out",
    "no_ssl_verify": False,
    "bypass_memory": False,
    "log_level": "INFO"
}

response = requests.post(submit_url, json=payload)
task_data = response.json()
task_id = task_data["task_id"]

print(f"Task submitted: {task_id}")
print(f"Status: {task_data['status']}")

# Poll for completion
status_url = f"http://localhost:8000/task/{task_id}"
while True:
    response = requests.get(status_url)
    task_status = response.json()

    print(f"Current status: {task_status['status']}")

    if task_status['status'] in ['completed', 'failed']:
        if task_status['result']:
            print(f"Success: {task_status['result']['success']}")
            print(f"Exit code: {task_status['result']['exit_code']}")
            print(f"Output: {task_status['result']['output'][:200]}...")
        break

    time.sleep(2)  # Wait 2 seconds before checking again
```

## Interactive API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Notes

- **Async Processing**: All tasks run asynchronously in the background
- **Task Storage**: Tasks are stored in-memory (will be lost on restart)
- **CLI Execution**: Uses Click's CliRunner to invoke the actual CLI command
- **Concurrency**: Multiple tasks can run concurrently
- **Output**: All artifacts are saved to the specified output directory
- **Monitoring**: Use the `/task/{task_id}` endpoint to poll for completion
- **RSS Feeds**: Automatically detected and processed by the underlying CLI
