#!/usr/bin/env python3
"""
Example script to monitor agent_b_web tasks via the REST API.
"""

import requests
import time
import sys
from typing import List, Dict, Any


API_BASE_URL = "http://localhost:8200"


def get_health() -> Dict[str, Any]:
    """Get service health status."""
    response = requests.get(f"{API_BASE_URL}/health")
    response.raise_for_status()
    return response.json()


def list_tasks(status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    List all tasks with optional filtering.

    Args:
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of tasks to return
    """
    params = {"limit": limit}
    if status:
        params["status"] = status

    response = requests.get(f"{API_BASE_URL}/tasks", params=params)
    response.raise_for_status()
    data = response.json()
    return data["tasks"]


def get_task(task_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific task."""
    response = requests.get(f"{API_BASE_URL}/tasks/{task_id}")
    response.raise_for_status()
    data = response.json()
    return data["task"]


def monitor_task(task_id: str, poll_interval: int = 5):
    """
    Monitor a task until it completes or fails.

    Args:
        task_id: The task ID to monitor
        poll_interval: Seconds to wait between checks
    """
    print(f"Monitoring task: {task_id}")
    print("-" * 60)

    while True:
        try:
            task = get_task(task_id)
            status = task["status"]

            print(f"Status: {status}")
            if status == "running":
                print(f"  Started: {task.get('started_at', 'N/A')}")
                print(f"  Files processed: {task.get('file_count', 'N/A')}")
            elif status == "completed":
                print(f"  Completed: {task['completed_at']}")
                print(f"  Files processed: {task['file_count']}")
                print(f"  Merged file: {task.get('merged_file', 'N/A')}")
                print("\n✅ Task completed successfully!")
                break
            elif status == "failed":
                print(f"  Failed: {task['completed_at']}")
                print(f"  Error: {task.get('error', 'Unknown error')}")
                print("\n❌ Task failed!")
                sys.exit(1)

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            break
        except Exception as e:
            print(f"Error checking task: {e}")
            time.sleep(poll_interval)


def show_task_summary():
    """Display a summary of all tasks."""
    print("=" * 60)
    print("Agent B Web - Task Summary")
    print("=" * 60)

    # Get health
    health = get_health()
    print(f"Service Status: {health['status']}")
    print(f"Total Tasks: {health['total_tasks']}")
    print()

    # Get tasks by status
    statuses = ["running", "pending", "completed", "failed"]
    for status in statuses:
        tasks = list_tasks(status=status, limit=10)
        print(f"{status.upper()}: {len(tasks)}")

        if tasks:
            for task in tasks[:5]:  # Show first 5
                print(f"  - {task['task_id'][:8]}... ({task['created_at']})")

            if len(tasks) > 5:
                print(f"  ... and {len(tasks) - 5} more")
        print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor agent_b_web tasks")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show task summary"
    )
    parser.add_argument(
        "--list",
        choices=["all", "pending", "running", "completed", "failed"],
        help="List tasks by status"
    )
    parser.add_argument(
        "--monitor",
        metavar="TASK_ID",
        help="Monitor a specific task until completion"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)"
    )

    args = parser.parse_args()

    try:
        if args.summary:
            show_task_summary()
        elif args.list:
            status = None if args.list == "all" else args.list
            tasks = list_tasks(status=status)
            print(f"Found {len(tasks)} tasks:")
            for task in tasks:
                print(f"  {task['task_id']}: {task['status']} ({task['created_at']})")
        elif args.monitor:
            monitor_task(args.monitor, args.interval)
        else:
            parser.print_help()

    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to agent_b_web API")
        print(f"Make sure the service is running at {API_BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
