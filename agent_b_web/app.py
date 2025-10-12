"""
Agent B Web - RabbitMQ Consumer and CTI JSON Processor

Listens to RabbitMQ queue "data.ingest.done" and processes CTI JSON files:
1. Reads all JSON files from /app/out
2. Transforms "summary" field to "text" field
3. Merges all JSON into one array
4. Saves to /app/pending
5. Executes chunk_and_ingest.py with the merged file
6. Deletes the temporary merged file

Features:
- Background task processing using ThreadPoolExecutor
- Concurrent message handling (configurable via MAX_WORKERS)
- Thread-safe message acknowledgment
- Graceful shutdown with task completion wait
"""

import json
import logging
import os
import sys
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Add parent directory to path to import agent_b modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_b.scripts.chunk_and_ingest import main as chunk_and_ingest_main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "root")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "toor")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "data.ingest.done")

OUT_DIR = Path(os.getenv("OUT_DIR", "/app/out"))
PENDING_DIR = Path(os.getenv("PENDING_DIR", "/app/pending"))

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "heva_docs")

# FastAPI configuration
API_PORT = int(os.getenv("API_PORT", "8200"))

# In-memory storage for task tracking
tasks_storage: Dict[str, dict] = {}
tasks_lock = threading.Lock()

# FastAPI app
app = FastAPI(
    title="Agent B Web - CTI Processor API",
    description="API for monitoring CTI JSON processing tasks",
    version="1.0.0"
)


# Pydantic models
class TaskInfo(BaseModel):
    """Model for task information."""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    message_data: Optional[Dict[str, Any]] = None
    file_count: Optional[int] = None
    merged_file: Optional[str] = None
    error: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""
    total: int
    tasks: List[TaskInfo]


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task: TaskInfo


# FastAPI endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent B Web - CTI Processor API",
        "endpoints": {
            "/tasks": "GET - List all tasks",
            "/tasks/{task_id}": "GET - Get specific task status",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent_b_cti_processor",
        "rabbitmq_connected": True,  # Could add actual connection check
        "total_tasks": len(tasks_storage)
    }


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(status: Optional[str] = None, limit: int = 100):
    """
    List all tasks.

    Args:
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of tasks to return
    """
    with tasks_lock:
        all_tasks = list(tasks_storage.values())

    # Filter by status if specified
    if status:
        all_tasks = [t for t in all_tasks if t.get("status") == status]

    # Sort by created_at descending (newest first)
    all_tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    # Apply limit
    all_tasks = all_tasks[:limit]

    # Convert to TaskInfo models
    task_infos = [TaskInfo(**task) for task in all_tasks]

    return TaskListResponse(total=len(task_infos), tasks=task_infos)


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status and details of a specific task.

    Args:
        task_id: The task ID to retrieve
    """
    with tasks_lock:
        task_data = tasks_storage.get(task_id)

    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskStatusResponse(task=TaskInfo(**task_data))


def transform_summary_to_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform 'summary' field to 'text' field in a JSON object.

    Args:
        data: JSON object that may contain a 'summary' field

    Returns:
        Transformed JSON object with 'text' field
    """
    if "summary" in data:
        data["text"] = data.pop("summary")
    return data


def load_and_transform_json_files(directory: Path) -> List[Dict[str, Any]]:
    """
    Load all JSON files from a directory and transform them.

    Args:
        directory: Path to directory containing JSON files

    Returns:
        List of transformed JSON objects
    """
    transformed_data = []
    json_files = list(directory.glob("*.json"))

    logger.info(f"Found {len(json_files)} JSON files in {directory}")

    for json_file in json_files:
        try:
            logger.info(f"Processing file: {json_file.name}")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Transform the data
            transformed = transform_summary_to_text(data)
            transformed_data.append(transformed)

            logger.info(f"Successfully processed: {json_file.name}")

        except Exception as e:
            logger.error(f"Failed to process {json_file.name}: {e}", exc_info=True)

    return transformed_data


def merge_and_save(data: List[Dict[str, Any]], output_dir: Path) -> Path:
    """
    Merge all JSON objects into one array and save to file.

    Args:
        data: List of JSON objects to merge
        output_dir: Directory to save the merged file

    Returns:
        Path to the saved merged file
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"merged_cti_{timestamp}.json"

    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Merged {len(data)} records into {output_file}")
    logger.info(f"File size: {output_file.stat().st_size / 1024:.2f} KB")

    return output_file


def execute_chunk_and_ingest(filepath: Path):
    """
    Execute the chunk_and_ingest.py main function with the given filepath.

    Args:
        filepath: Path to the JSON file to process
    """
    logger.info(f"Executing chunk_and_ingest with file: {filepath}")

    # Save original sys.argv
    original_argv = sys.argv.copy()

    try:
        # Set up arguments for chunk_and_ingest
        sys.argv = [
            "chunk_and_ingest.py",
            "--src", str(filepath),
            "--collection", QDRANT_COLLECTION,
            "--qdrant-url", QDRANT_URL,
            "--create-indexes"
        ]

        # Execute the main function
        chunk_and_ingest_main()

        logger.info("chunk_and_ingest completed successfully")

    except Exception as e:
        logger.error(f"Failed to execute chunk_and_ingest: {e}", exc_info=True)
        raise
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


def process_message(message_data: Dict[str, Any], task_id: str):
    """
    Process a message received from RabbitMQ.

    Steps:
    1. Load all JSON files from OUT_DIR
    2. Transform 'summary' to 'text'
    3. Merge into single JSON array
    4. Save to PENDING_DIR
    5. Execute chunk_and_ingest
    6. Delete temporary file

    Args:
        message_data: The message data from RabbitMQ
        task_id: Unique task ID for tracking
    """
    logger.info("=" * 60)
    logger.info(f"[Task {task_id}] Processing new message from RabbitMQ")
    logger.info("=" * 60)
    logger.info(f"Message data: {json.dumps(message_data, indent=2)}")

    # Update task status to running
    with tasks_lock:
        tasks_storage[task_id]["status"] = "running"
        tasks_storage[task_id]["started_at"] = datetime.now().isoformat()

    merged_file = None

    try:
        # Step 1 & 2: Load and transform JSON files
        logger.info(f"[Task {task_id}] Step 1-2: Loading and transforming JSON files from {OUT_DIR}")
        transformed_data = load_and_transform_json_files(OUT_DIR)

        if not transformed_data:
            logger.warning(f"[Task {task_id}] No JSON files found or all files failed to process")
            with tasks_lock:
                tasks_storage[task_id]["status"] = "completed"
                tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
                tasks_storage[task_id]["file_count"] = 0
            return

        # Update task with file count
        with tasks_lock:
            tasks_storage[task_id]["file_count"] = len(transformed_data)

        # Step 3 & 4: Merge and save
        logger.info(f"[Task {task_id}] Step 3-4: Merging {len(transformed_data)} records and saving to {PENDING_DIR}")
        merged_file = merge_and_save(transformed_data, PENDING_DIR)

        # Update task with merged file path
        with tasks_lock:
            tasks_storage[task_id]["merged_file"] = str(merged_file)

        # Step 5: Execute chunk_and_ingest
        logger.info(f"[Task {task_id}] Step 5: Executing chunk_and_ingest")
        execute_chunk_and_ingest(merged_file)

        # Step 6: Delete temporary file
        logger.info(f"[Task {task_id}] Step 6: Deleting temporary file {merged_file}")
        merged_file.unlink()
        logger.info(f"[Task {task_id}] Successfully deleted {merged_file}")

        # Update task status to completed
        with tasks_lock:
            tasks_storage[task_id]["status"] = "completed"
            tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info(f"[Task {task_id}] Message processing completed successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"[Task {task_id}] Failed to process message: {e}", exc_info=True)

        # Update task status to failed
        with tasks_lock:
            tasks_storage[task_id]["status"] = "failed"
            tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
            tasks_storage[task_id]["error"] = str(e)

        # Don't delete the merged file if processing failed
        if merged_file and merged_file.exists():
            logger.info(f"[Task {task_id}] Keeping merged file for debugging: {merged_file}")


def process_message_wrapper(channel, method, body):
    """
    Wrapper function to process message in background thread.
    Handles acknowledgment after processing completes.
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    try:
        # Parse message body
        message_data = json.loads(body)
        logger.info(f"[Task {task_id}] Processing message from queue: {RABBITMQ_QUEUE}")

        # Create task record
        with tasks_lock:
            tasks_storage[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "message_data": message_data,
                "file_count": None,
                "merged_file": None,
                "error": None
            }

        # Process the message
        process_message(message_data, task_id)

        # Acknowledge the message on the main thread
        channel.connection.add_callback_threadsafe(
            lambda: channel.basic_ack(delivery_tag=method.delivery_tag)
        )

        logger.info(f"[Task {task_id}] Message processed and acknowledged successfully")

    except Exception as e:
        logger.error(f"[Task {task_id}] Error processing message: {e}", exc_info=True)

        # Update task with error if it exists
        with tasks_lock:
            if task_id in tasks_storage:
                tasks_storage[task_id]["status"] = "failed"
                tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
                tasks_storage[task_id]["error"] = str(e)

        # Negative acknowledge - message will be requeued
        channel.connection.add_callback_threadsafe(
            lambda: channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        )


def on_message(channel, method, properties, body, executor):
    """
    Callback function for RabbitMQ message consumption.
    Submits processing to background thread pool.
    """
    logger.info(f"Received message from queue: {RABBITMQ_QUEUE}")
    logger.info(f"Submitting message to background task executor")

    # Submit message processing to thread pool
    executor.submit(process_message_wrapper, channel, method, body)


def start_consumer():
    """
    Start the RabbitMQ consumer and listen for messages.
    """
    # Get max workers from environment or default to 4
    max_workers = int(os.getenv("MAX_WORKERS", "4"))

    logger.info("=" * 60)
    logger.info("Agent B Web - CTI JSON Processor")
    logger.info("=" * 60)
    logger.info(f"RabbitMQ Host: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    logger.info(f"Queue: {RABBITMQ_QUEUE}")
    logger.info(f"Out Directory: {OUT_DIR}")
    logger.info(f"Pending Directory: {PENDING_DIR}")
    logger.info(f"Qdrant URL: {QDRANT_URL}")
    logger.info(f"Qdrant Collection: {QDRANT_COLLECTION}")
    logger.info(f"Max Background Workers: {max_workers}")
    logger.info("=" * 60)

    # Ensure directories exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    # Create thread pool executor for background processing
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="MessageProcessor") as executor:
        while True:
            try:
                # Connect to RabbitMQ
                logger.info("Connecting to RabbitMQ...")
                credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
                parameters = pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )

                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()

                # Declare queue (idempotent)
                channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

                # Set QoS - prefetch up to max_workers messages for parallel processing
                # This allows the worker pool to process multiple messages concurrently
                channel.basic_qos(prefetch_count=max_workers)

                # Start consuming with executor passed to callback
                logger.info(f"✅ Connected to RabbitMQ. Listening for messages on queue '{RABBITMQ_QUEUE}'...")
                logger.info(f"Processing up to {max_workers} messages concurrently")
                channel.basic_consume(
                    queue=RABBITMQ_QUEUE,
                    on_message_callback=lambda ch, method, properties, body: on_message(
                        ch, method, properties, body, executor
                    )
                )

                channel.start_consuming()

            except KeyboardInterrupt:
                logger.info("Shutting down consumer...")
                logger.info("Waiting for background tasks to complete...")
                break
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)

    logger.info("All background tasks completed. Shutdown complete.")


def run_api_server():
    """Run the FastAPI server."""
    logger.info(f"Starting FastAPI server on port {API_PORT}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent B Web - CTI JSON Processor")
    parser.add_argument("--test", action="store_true", help="Run in test mode (process once and exit)")
    parser.add_argument("--api-only", action="store_true", help="Run API server only (no consumer)")
    parser.add_argument("--consumer-only", action="store_true", help="Run consumer only (no API)")
    args = parser.parse_args()

    if args.test:
        logger.info("Running in TEST mode - processing files once")
        test_task_id = str(uuid.uuid4())
        test_message = {"test": True, "timestamp": datetime.now().isoformat()}

        # Create task record for test
        with tasks_lock:
            tasks_storage[test_task_id] = {
                "task_id": test_task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "message_data": test_message,
                "file_count": None,
                "merged_file": None,
                "error": None
            }

        process_message(test_message, test_task_id)
    elif args.api_only:
        logger.info("Running in API-ONLY mode")
        run_api_server()
    elif args.consumer_only:
        logger.info("Running in CONSUMER-ONLY mode")
        start_consumer()
    else:
        # Run both API server and consumer concurrently
        logger.info("Starting both API server and RabbitMQ consumer...")

        # Start API server in a separate thread
        api_thread = threading.Thread(target=run_api_server, daemon=True, name="APIServer")
        api_thread.start()

        # Give API server time to start
        time.sleep(2)
        logger.info(f"✅ API server started at http://0.0.0.0:{API_PORT}")

        # Start consumer in main thread (blocking)
        try:
            start_consumer()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            logger.info("Waiting for API server to shut down...")


if __name__ == "__main__":
    main()
