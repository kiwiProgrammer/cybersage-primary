# Agent B Web Examples

Example scripts for interacting with the agent_b_web REST API and consuming RabbitMQ events.

## monitor_tasks.py

A Python script for monitoring task processing via the API.

### Requirements

```bash
pip install requests
```

### Usage

**Show task summary:**
```bash
./monitor_tasks.py --summary
```

Output:
```
============================================================
Agent B Web - Task Summary
============================================================
Service Status: healthy
Total Tasks: 15

RUNNING: 2
  - 123e4567... (2025-10-12T00:00:00)
  - 234e5678... (2025-10-12T00:01:00)

PENDING: 1
  - 345e6789... (2025-10-12T00:02:00)

COMPLETED: 10
  - 456e789a... (2025-10-12T00:03:00)
  - 567e89ab... (2025-10-12T00:04:00)
  ... and 8 more

FAILED: 2
  - 678e9abc... (2025-10-12T00:05:00)
  - 789eabcd... (2025-10-12T00:06:00)
```

**List all tasks:**
```bash
./monitor_tasks.py --list all
```

**List tasks by status:**
```bash
# List only running tasks
./monitor_tasks.py --list running

# List completed tasks
./monitor_tasks.py --list completed

# List failed tasks
./monitor_tasks.py --list failed
```

**Monitor a specific task:**
```bash
./monitor_tasks.py --monitor 123e4567-e89b-12d3-a456-426614174000
```

Output:
```
Monitoring task: 123e4567-e89b-12d3-a456-426614174000
------------------------------------------------------------
Status: running
  Started: 2025-10-12T00:00:01
  Files processed: 10
Status: running
  Started: 2025-10-12T00:00:01
  Files processed: 10
Status: completed
  Completed: 2025-10-12T00:05:30
  Files processed: 10
  Merged file: /app/pending/merged_cti_20251012_000000.json

✅ Task completed successfully!
```

**Monitor with custom poll interval:**
```bash
# Check every 10 seconds instead of default 5
./monitor_tasks.py --monitor 123e4567-e89b-12d3-a456-426614174000 --interval 10
```

## consume_history_graph.py

A Python script demonstrating how to consume completion events from the `history.graph.done` queue.

### Requirements

```bash
pip install pika
```

### Usage

**Run the consumer:**
```bash
./consume_history_graph.py
```

Output:
```
============================================================
History Graph Done Queue Consumer
============================================================
RabbitMQ Host: localhost:5672
Queue: history.graph.done
============================================================
Connecting to RabbitMQ...
✅ Connected. Listening for messages on queue 'history.graph.done'...
Press CTRL+C to exit
============================================================
```

**When a message is received:**
```
============================================================
Received completion event from agent_b_web
============================================================
Task ID: 123e4567-e89b-12d3-a456-426614174000
Timestamp: 2025-10-12T00:05:30.123456
Status: completed
Completed At: 2025-10-12T00:05:30
File Count: 10
Collection: heva_docs
Qdrant URL: http://qdrant:6333
Processing completed successfully
============================================================
Message acknowledged
```

### Integration

This script serves as a template for downstream services that need to:
- Build knowledge graphs from ingested CTI data
- Generate summaries and reports
- Create visualizations
- Trigger additional analysis pipelines

### Customization

Edit the `process_completion_event()` function to add your custom processing logic:

```python
def process_completion_event(message_data):
    """Process completion event."""
    data = message_data.get("data", {})

    # Your custom processing here
    collection = data.get("collection")
    qdrant_url = data.get("qdrant_url")

    # Example: Query Qdrant for the ingested data
    # client = QdrantClient(url=qdrant_url)
    # results = client.scroll(collection_name=collection, limit=100)

    # Example: Build knowledge graph
    # build_knowledge_graph(results)

    # Example: Generate summary report
    # generate_summary_report(results)
```

## Using with curl

Simple examples using curl:

**List all tasks:**
```bash
curl http://localhost:8200/tasks | jq
```

**Get task details:**
```bash
curl http://localhost:8200/tasks/123e4567-e89b-12d3-a456-426614174000 | jq
```

**Filter running tasks:**
```bash
curl "http://localhost:8200/tasks?status=running" | jq
```

**Check service health:**
```bash
curl http://localhost:8200/health | jq
```

## Integration Examples

### Python

```python
import requests

# List all tasks
response = requests.get("http://localhost:8200/tasks")
tasks = response.json()["tasks"]

for task in tasks:
    print(f"Task {task['task_id']}: {task['status']}")
```

### JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

async function getTasks() {
  const response = await fetch('http://localhost:8200/tasks');
  const data = await response.json();
  return data.tasks;
}

getTasks().then(tasks => {
  tasks.forEach(task => {
    console.log(`Task ${task.task_id}: ${task.status}`);
  });
});
```

### Bash

```bash
#!/bin/bash

# Get all running tasks
TASKS=$(curl -s "http://localhost:8200/tasks?status=running" | jq -r '.tasks[].task_id')

# Monitor each task
for task_id in $TASKS; do
  echo "Checking task: $task_id"
  curl -s "http://localhost:8200/tasks/$task_id" | jq '.task.status'
done
```
