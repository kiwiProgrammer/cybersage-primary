"""
Agent C Queue - RabbitMQ Consumer for Vulnerability Analysis

Listens to RabbitMQ queue "history.graph.done" and processes CTI JSON files:
1. Reads all "cti_*_*.json" files from /app/out
2. For each file:
   a. Copies file to /app/temp for processing
   b. Adds "_id" field with filename (without extension)
   c. Calls agent_c POST /analyze endpoint
3. Ensures only 1 analysis task runs at a time (sequential processing)

Features:
- Sequential task processing (one at a time)
- REST API for task monitoring and status
- Shared /app/temp volume with agent_c
- Automatic task queue management
"""

import json
import logging
import os
import sys
import time
import threading
import uuid
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import requests
from queue import Queue

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

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
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "history.graph.done")

OUT_DIR = Path(os.getenv("OUT_DIR", "/app/out"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/app/temp"))
AGENT_C_URL = os.getenv("AGENT_C_URL", "http://autonomous-council-api:8000")

# FastAPI configuration
API_PORT = int(os.getenv("API_PORT", "8300"))

# In-memory storage for task tracking
tasks_storage: Dict[str, dict] = {}
tasks_lock = threading.Lock()

# Queue for sequential processing
analysis_queue = Queue()
current_task_id_lock = threading.Lock()
current_task_id = None

# FastAPI app
app = FastAPI(
    title="Agent C Queue - Analysis Queue API",
    description="API for monitoring vulnerability analysis queue",
    version="1.0.0"
)


# Pydantic models
class TaskInfo(BaseModel):
    """Model for task information."""
    task_id: str
    status: str  # "queued", "processing", "waiting_for_agent_c", "completed", "failed"
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    message_data: Optional[Dict[str, Any]] = None
    file_count: Optional[int] = None
    processed_files: Optional[List[str]] = None
    agent_c_task_id: Optional[str] = None
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
        "message": "Agent C Queue - Analysis Queue API",
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
    with current_task_id_lock:
        current = current_task_id

    return {
        "status": "healthy",
        "service": "agent_c_queue",
        "rabbitmq_connected": True,
        "total_tasks": len(tasks_storage),
        "queue_size": analysis_queue.qsize(),
        "current_task": current
    }


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(status: Optional[str] = None, limit: int = 100):
    """
    List all tasks.

    Args:
        status: Filter by status
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


def find_cti_files(directory: Path) -> List[Path]:
    """
    Find all files matching "cti_*_*.json" pattern in directory.

    Args:
        directory: Path to directory to search

    Returns:
        List of matching file paths
    """
    pattern = "*.json"
    files = list(directory.glob(pattern))
    logger.info(f"Found {len(files)} files matching '{pattern}' in {directory}")
    return files


def copy_and_add_id(source_file: Path, temp_dir: Path) -> Path:
    """
    Copy JSON file to temp directory and add "_id" field.

    Args:
        source_file: Source JSON file path
        temp_dir: Temporary directory to copy to

    Returns:
        Path to the processed file
    """
    # Ensure temp directory exists
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Copy file to temp directory
    temp_file = temp_dir / source_file.name
    shutil.copy2(source_file, temp_file)
    logger.info(f"Copied {source_file.name} to {temp_file}")

    # Read JSON content
    with open(temp_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add _id field (filename without extension)
    file_id = source_file.stem
    data["_id"] = file_id
    logger.info(f"Added '_id' field with value '{file_id}' to {temp_file.name}")

    # Write back to file
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return temp_file


def call_agent_c_analyze(incident_filepath: str) -> Optional[str]:
    """
    Call agent_c POST /analyze endpoint.

    Args:
        incident_filepath: Path to the incident file

    Returns:
        Task ID from agent_c, or None if failed
    """
    url = f"{AGENT_C_URL}/analyze"
    payload = {
        "incident_filepath": incident_filepath
    }

    try:
        logger.info(f"Calling agent_c /analyze endpoint: {url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        task_id = result.get("task_id")

        logger.info(f"Agent_c accepted task, task_id: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"Failed to call agent_c /analyze: {e}", exc_info=True)
        return None


def wait_for_agent_c_task(task_id: str, timeout: int = 3600, poll_interval: int = 30) -> bool:
    """
    Wait for agent_c task to complete by polling /tasks/{task_id} endpoint.

    Args:
        task_id: Agent_c task ID to monitor
        timeout: Maximum time to wait in seconds (default: 1 hour)
        poll_interval: Polling interval in seconds (default: 5 seconds)

    Returns:
        True if completed successfully, False if failed or timed out
    """
    url = f"{AGENT_C_URL}/tasks/{task_id}"
    start_time = time.time()

    logger.info(f"Waiting for agent_c task {task_id} to complete...")

    while True:
        try:
            # Check if we've exceeded timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Timeout waiting for agent_c task {task_id} after {timeout}s")
                return False

            # Poll agent_c for task status
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            status = result.get("status")

            logger.info(f"Agent_c task {task_id} status: {status}")

            if status == "completed":
                logger.info(f"Agent_c task {task_id} completed successfully")
                return True
            elif status == "failed":
                error = result.get("error", "Unknown error")
                logger.error(f"Agent_c task {task_id} failed: {error}")
                return False
            elif status == "not_found":
                logger.error(f"Agent_c task {task_id} got lost")
                return False
            elif status in ["pending", "running"]:
                # Still processing, wait and poll again
                time.sleep(poll_interval)
            else:
                logger.warning(f"Unknown status '{status}' for agent_c task {task_id}")
                time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error polling agent_c task {task_id}: {e}")
            time.sleep(poll_interval)


def process_analysis_task(task_id: str, message_data: Dict[str, Any]):
    """
    Process a single analysis task by finding CTI files and calling agent_c.
    Ensures sequential processing (one file at a time).

    Args:
        task_id: Unique task ID for tracking
        message_data: The message data from RabbitMQ
    """
    global current_task_id

    logger.info("=" * 60)
    logger.info(f"[Task {task_id}] Processing analysis task")
    logger.info("=" * 60)

    # Update current task
    with current_task_id_lock:
        current_task_id = task_id

    # Update task status to processing
    with tasks_lock:
        tasks_storage[task_id]["status"] = "processing"
        tasks_storage[task_id]["started_at"] = datetime.now().isoformat()

    try:
        # Step 1: Find all cti_*_*.json files
        logger.info(f"[Task {task_id}] Step 1: Finding CTI files in {OUT_DIR}")
        cti_files = find_cti_files(OUT_DIR)

        if not cti_files:
            logger.warning(f"[Task {task_id}] No CTI files found")
            with tasks_lock:
                tasks_storage[task_id]["status"] = "completed"
                tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
                tasks_storage[task_id]["file_count"] = 0
            return

        # Update task with file count
        with tasks_lock:
            tasks_storage[task_id]["file_count"] = len(cti_files)
            tasks_storage[task_id]["processed_files"] = []

        # Step 2: Process each file sequentially
        logger.info(f"[Task {task_id}] Step 2: Processing {len(cti_files)} files sequentially")

        for idx, cti_file in enumerate(cti_files, 1):
            logger.info(f"[Task {task_id}] Processing file {idx}/{len(cti_files)}: {cti_file.name}")

            # Step 2a: Copy file and add _id
            logger.info(f"[Task {task_id}] Step 2a: Copying file to temp and adding _id")
            temp_file = copy_and_add_id(cti_file, TEMP_DIR)

            # Step 2b: Call agent_c /analyze
            logger.info(f"[Task {task_id}] Step 2b: Calling agent_c /analyze")
            agent_c_task_id = call_agent_c_analyze(str(temp_file))

            if not agent_c_task_id:
                logger.error(f"[Task {task_id}] Failed to submit {cti_file.name} to agent_c")
                continue

            # Update task with agent_c task ID
            with tasks_lock:
                tasks_storage[task_id]["agent_c_task_id"] = agent_c_task_id
                tasks_storage[task_id]["status"] = "waiting_for_agent_c"

            # Step 2c: Wait for agent_c to complete
            logger.info(f"[Task {task_id}] Step 2c: Waiting for agent_c task {agent_c_task_id}")
            success = wait_for_agent_c_task(agent_c_task_id)

            if success:
                logger.info(f"[Task {task_id}] Successfully processed {cti_file.name}")
                with tasks_lock:
                    tasks_storage[task_id]["processed_files"].append(cti_file.name)
                    tasks_storage[task_id]["status"] = "processing"
            else:
                logger.error(f"[Task {task_id}] Failed to process {cti_file.name}")

        # Mark task as completed
        completed_at = datetime.now().isoformat()
        with tasks_lock:
            tasks_storage[task_id]["status"] = "completed"
            tasks_storage[task_id]["completed_at"] = completed_at

        logger.info("=" * 60)
        logger.info(f"[Task {task_id}] Analysis task completed")
        logger.info(f"[Task {task_id}] Processed {len(tasks_storage[task_id].get('processed_files', []))} files")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"[Task {task_id}] Failed to process analysis task: {e}", exc_info=True)

        # Update task status to failed
        with tasks_lock:
            tasks_storage[task_id]["status"] = "failed"
            tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
            tasks_storage[task_id]["error"] = str(e)

    finally:
        # Clear current task
        with current_task_id_lock:
            current_task_id = None


def task_processor_worker():
    """
    Background worker that processes tasks from the queue sequentially.
    """
    logger.info("Task processor worker started")

    while True:
        try:
            # Get next task from queue (blocking)
            task_id, message_data = analysis_queue.get(block=True)

            logger.info(f"Task processor picked up task {task_id} from queue")

            # Process the task
            process_analysis_task(task_id, message_data)

            # Mark task as done
            analysis_queue.task_done()

        except Exception as e:
            logger.error(f"Error in task processor worker: {e}", exc_info=True)
            time.sleep(1)


def on_message(channel, method, properties, body):
    """
    Callback function for RabbitMQ message consumption.
    Adds tasks to the queue for sequential processing.
    """
    logger.info(f"Received message from queue: {RABBITMQ_QUEUE}")

    try:
        # Parse message body
        message_data = json.loads(body)

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        logger.info(f"[Task {task_id}] Creating new analysis task")

        # Create task record
        with tasks_lock:
            tasks_storage[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "message_data": message_data,
                "file_count": None,
                "processed_files": None,
                "agent_c_task_id": None,
                "error": None
            }

        # Add task to queue
        analysis_queue.put((task_id, message_data))
        logger.info(f"[Task {task_id}] Added to analysis queue (queue size: {analysis_queue.qsize()})")

        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[Task {task_id}] Message acknowledged")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Negative acknowledge - message will be requeued
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_consumer():
    """
    Start the RabbitMQ consumer and listen for messages.
    """
    logger.info("=" * 60)
    logger.info("Agent C Queue - Vulnerability Analysis Queue")
    logger.info("=" * 60)
    logger.info(f"RabbitMQ Host: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    logger.info(f"Queue: {RABBITMQ_QUEUE}")
    logger.info(f"Out Directory: {OUT_DIR}")
    logger.info(f"Temp Directory: {TEMP_DIR}")
    logger.info(f"Agent C URL: {AGENT_C_URL}")
    logger.info("=" * 60)

    # Ensure directories exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Start task processor worker in background thread
    processor_thread = threading.Thread(target=task_processor_worker, daemon=True, name="TaskProcessor")
    processor_thread.start()
    logger.info("Task processor worker started in background")

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

            # Set QoS - prefetch 1 message at a time
            channel.basic_qos(prefetch_count=1)

            # Start consuming
            logger.info(f"✅ Connected to RabbitMQ. Listening for messages on queue '{RABBITMQ_QUEUE}'...")
            logger.info("Processing tasks sequentially (one at a time)")
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=on_message
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

    logger.info("Shutdown complete.")


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
    parser = argparse.ArgumentParser(description="Agent C Queue - Vulnerability Analysis Queue")
    parser.add_argument("--api-only", action="store_true", help="Run API server only (no consumer)")
    parser.add_argument("--consumer-only", action="store_true", help="Run consumer only (no API)")
    args = parser.parse_args()

    if args.api_only:
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
