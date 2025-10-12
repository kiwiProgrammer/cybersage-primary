# RabbitMQ Package

A reusable RabbitMQ messaging package for publishing messages to queues across agent services.

## Features

- Simple, clean API for publishing messages to RabbitMQ queues
- Automatic timestamp and task_id handling
- Environment variable configuration
- Connection management with proper cleanup
- Comprehensive error handling and logging

## Installation

Add `pika>=1.3.0` to your requirements.txt:

```
pika>=1.3.0
```

## Configuration

The package reads connection settings from environment variables:

- `RABBITMQ_HOST` - RabbitMQ host (default: "rabbitmq")
- `RABBITMQ_PORT` - RabbitMQ port (default: 5672)
- `RABBITMQ_USER` - RabbitMQ username (default: "root")
- `RABBITMQ_PASS` - RabbitMQ password (default: "toor")

## Usage

### Quick Start - Convenience Function

```python
from rabbitmq import publish_message

# Publish with automatic timestamp and task_id
success = publish_message(
    queue_name="data.ingest.done",
    message={"response": response_data},
    task_id="task-123"
)

if success:
    print("Message published successfully")
```

### Advanced Usage - Publisher Class

```python
from rabbitmq import RabbitMQPublisher

# Create a publisher instance
publisher = RabbitMQPublisher(
    host="rabbitmq",
    port=5672,
    username="root",
    password="toor"
)

# Publish a simple message
message = {"status": "completed", "data": {"count": 42}}
publisher.publish("my.queue", message)

# Publish with automatic timestamp and task_id
publisher.publish_with_timestamp(
    queue_name="my.queue",
    data={"result": "success"},
    task_id="task-456"
)
```

## Message Format

When using `publish_with_timestamp()`, messages are automatically wrapped:

```json
{
  "timestamp": "2025-10-12T00:00:00.000000",
  "task_id": "task-123",
  "data": {
    "response": {
      "success": true,
      "exit_code": 0,
      "output": "...",
      "error": null
    }
  }
}
```

## Queue Configuration

All queues are created as:
- **Durable**: Queue survives RabbitMQ restarts
- **Persistent**: Messages survive RabbitMQ restarts

## Error Handling

All functions return a boolean indicating success:

```python
success = publish_message("my.queue", {"data": "value"})

if not success:
    # Handle failure - error is automatically logged
    logger.error("Failed to publish message")
```

Errors are automatically logged with full stack traces for debugging.

## Integration Example

```python
from rabbitmq import publish_message

# After task completion
run_response = RunResponse(
    success=True,
    exit_code=0,
    output="Task completed",
    error=None
)

# Publish to event bus
success = publish_message(
    queue_name="data.ingest.done",
    message={"response": run_response.model_dump()},
    task_id=task_id
)
```

## Available Queues

The system has the following pre-configured queues:

- `data.ingest.done` - Data ingestion completion events
- `history.graph.done` - History graph processing completion events
- `debate.done` - Debate completion events

## Thread Safety

The `RabbitMQPublisher` creates a new connection for each publish operation and properly closes it afterward, making it safe to use across threads and async contexts.
