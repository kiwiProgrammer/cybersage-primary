"""FastAPI web interface for agent_a CTI pipeline."""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import agent_a modules FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from click.testing import CliRunner
from agent_a.app.cli import cli

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from agent_a.app.logging_conf import setup_logging
from rabbitmq import publish_message

# Setup logging
setup_logging('INFO')
logger = logging.getLogger(__name__)

# In-memory storage for task results
tasks_storage: Dict[str, dict] = {}

app = FastAPI(
    title="Agent A CTI Pipeline API",
    description="API for processing CTI URLs through the agentic pipeline",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    print("\n" + "=" * 60)
    print("  Agent A CTI Pipeline API - Starting Up")
    print("=" * 60)
    print(f"  Version: 1.0.0")
    print(f"  Service: agent_a_cti_pipeline")
    print(f"  Time: {datetime.now().isoformat()}")
    print("=" * 60)
    print("\nEndpoints available:")
    print("  GET  /            - Root endpoint")
    print("  GET  /health      - Health check")
    print("  POST /run         - Submit async task")
    print("  GET  /task/{id}   - Check task status")
    print("  GET  /docs        - API documentation")
    print("=" * 60 + "\n")
    logger.info("Agent A Web API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    print("\n" + "=" * 60)
    print("  Agent A CTI Pipeline API - Shutting Down")
    print("=" * 60)
    print(f"  Active tasks in storage: {len(tasks_storage)}")
    print(f"  Time: {datetime.now().isoformat()}")
    print("=" * 60 + "\n")
    logger.info("Agent A Web API shutting down")


class RunRequest(BaseModel):
    """Request model for CLI run command."""
    urls: List[str] = Field(..., description="List of URLs to process", min_items=1)
    output_dir: str = Field(default="./out", description="Output directory for artifacts")
    auth_username: Optional[str] = Field(None, description="Username for HTTP basic authentication")
    auth_password: Optional[str] = Field(None, description="Password for HTTP basic authentication")
    no_ssl_verify: bool = Field(False, description="Disable SSL certificate verification")
    bypass_memory: bool = Field(False, description="Bypass memory check and reprocess URLs")
    log_level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")


class RunResponse(BaseModel):
    """Response model for CLI run command execution."""
    success: bool
    exit_code: int
    output: str
    error: Optional[str] = None


class TaskSubmitResponse(BaseModel):
    """Response model for task submission."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    submitted_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[RunResponse] = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent A CTI Pipeline API",
        "endpoints": {
            "/run": "POST - Execute CLI run command (async)",
            "/task/{task_id}": "GET - Check task status and results",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent_a_cti_pipeline"}


async def execute_cli_command(task_id: str, request: RunRequest):
    """
    Background task to execute the CLI command.
    """
    print(f"[TASK {task_id}] ========================================")
    print(f"[TASK {task_id}] Starting execution for {len(request.urls)} URLs")
    print(f"[TASK {task_id}] URLs: {', '.join(request.urls)}")
    print(f"[TASK {task_id}] Output directory: {request.output_dir}")
    print(f"[TASK {task_id}] Log level: {request.log_level}")
    print(f"[TASK {task_id}] ========================================")
    logger.info(f"Task {task_id}: Starting execution for {len(request.urls)} URLs")

    # Update task status to running
    tasks_storage[task_id]["status"] = "running"
    tasks_storage[task_id]["started_at"] = datetime.now().isoformat()

    start_time = datetime.now()
    print(f"[TASK {task_id}] Status: RUNNING at {start_time.isoformat()}")

    # Create a CliRunner to invoke the Click command
    runner = CliRunner()

    # Build the command arguments
    args = ["run"] + list(request.urls)

    # Use OUTPUT_DIR environment variable, fallback to request value or default
    output_dir = os.getenv("OUTPUT_DIR", request.output_dir)
    args.extend(["--output-dir", output_dir])

    if request.auth_username:
        args.extend(["--auth-username", request.auth_username])
    if request.auth_password:
        args.extend(["--auth-password", "***"])  # Don't log password
    if request.no_ssl_verify:
        args.append("--no-ssl-verify")
    if request.bypass_memory:
        args.append("--bypass-memory")

    # Add log level to parent CLI group
    cli_args = ["--log-level", request.log_level] + args

    try:
        # Invoke the CLI command in a thread pool to avoid blocking
        logger.info(f"Task {task_id}: Invoking CLI with args: {cli_args}")

        # Run the blocking CLI command in an executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: runner.invoke(cli, cli_args, catch_exceptions=False)
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        success = result.exit_code == 0

        print(f"[TASK {task_id}] ========================================")
        print(f"[TASK {task_id}] CLI execution completed")
        print(f"[TASK {task_id}] Exit code: {result.exit_code}")
        print(f"[TASK {task_id}] Success: {success}")
        print(f"[TASK {task_id}] Duration: {duration:.2f} seconds")
        print(f"[TASK {task_id}] Output length: {len(result.output)} characters")
        if not success:
            print(f"[TASK {task_id}] ERROR: Command failed with exit code {result.exit_code}")
        print(f"[TASK {task_id}] ========================================")

        run_response = RunResponse(
            success=success,
            exit_code=result.exit_code,
            output=result.output,
            error=None if success else f"Command failed with exit code {result.exit_code}"
        )

        # Publish to RabbitMQ
        success_published = publish_message(
            queue_name="data.ingest.done",
            message={"response": run_response.model_dump()},
            task_id=task_id
        )
        if success_published:
            logger.info(f"Task {task_id}: Published to RabbitMQ queue 'data.ingest.done'")
            print(f"[TASK {task_id}] Published to RabbitMQ queue: data.ingest.done")
        else:
            logger.error(f"Task {task_id}: Failed to publish to RabbitMQ")
            print(f"[TASK {task_id}] ERROR: Failed to publish to RabbitMQ")

        # Update task with results
        tasks_storage[task_id]["status"] = "completed"
        tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
        tasks_storage[task_id]["result"] = run_response.model_dump()

        print(f"[TASK {task_id}] Status: COMPLETED at {end_time.isoformat()}")
        logger.info(f"Task {task_id}: Completed successfully in {duration:.2f}s")

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"[TASK {task_id}] ========================================")
        print(f"[TASK {task_id}] EXCEPTION OCCURRED")
        print(f"[TASK {task_id}] Error: {str(e)}")
        print(f"[TASK {task_id}] Duration before failure: {duration:.2f} seconds")
        print(f"[TASK {task_id}] ========================================")
        logger.error(f"Task {task_id}: CLI command execution failed: {e}", exc_info=True)

        run_response = RunResponse(
            success=False,
            exit_code=1,
            output="",
            error=str(e)
        )

        # Publish to RabbitMQ
        success_published = publish_message(
            queue_name="data.ingest.done",
            message={"response": run_response.model_dump()},
            task_id=task_id
        )
        if success_published:
            logger.info(f"Task {task_id}: Published error to RabbitMQ queue 'data.ingest.done'")
            print(f"[TASK {task_id}] Published error to RabbitMQ queue: data.ingest.done")
        else:
            logger.error(f"Task {task_id}: Failed to publish error to RabbitMQ")
            print(f"[TASK {task_id}] ERROR: Failed to publish error to RabbitMQ")

        # Update task with error
        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["completed_at"] = datetime.now().isoformat()
        tasks_storage[task_id]["result"] = run_response.model_dump()

        print(f"[TASK {task_id}] Status: FAILED at {end_time.isoformat()}")


@app.post("/run", response_model=TaskSubmitResponse)
async def run_cli_command(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Submit the agent_a CLI run command for execution.

    This endpoint submits the task and returns immediately with a task_id.
    Use the /task/{task_id} endpoint to check the status and retrieve results.
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    print(f"\n[API] ========================================")
    print(f"[API] New task submission received")
    print(f"[API] Task ID: {task_id}")
    print(f"[API] URLs: {', '.join(request.urls)}")
    print(f"[API] Output directory: {request.output_dir}")
    print(f"[API] ========================================\n")

    # Initialize task in storage
    tasks_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "submitted_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None
    }

    # Add background task
    background_tasks.add_task(execute_cli_command, task_id, request)

    logger.info(f"Task {task_id}: Submitted for execution with {len(request.urls)} URLs")

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message=f"Task submitted successfully. Use /task/{task_id} to check status."
    )


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status and results of a submitted task.
    """
    if task_id not in tasks_storage:
        print(f"[API] Task status check: Task {task_id} NOT FOUND")
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task_data = tasks_storage[task_id]
    print(f"[API] Task status check: {task_id} - Status: {task_data['status']}")

    return TaskStatusResponse(
        task_id=task_data["task_id"],
        status=task_data["status"],
        submitted_at=task_data["submitted_at"],
        started_at=task_data["started_at"],
        completed_at=task_data["completed_at"],
        result=RunResponse(**task_data["result"]) if task_data["result"] else None
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)