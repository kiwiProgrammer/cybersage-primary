#!/usr/bin/env python3
"""
Example consumer for the "history.graph.done" RabbitMQ queue.

This demonstrates how downstream services can consume completion events
from agent_b_web after CTI data has been processed and ingested into Qdrant.
"""

import json
import logging
import os
import pika
import sys

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "root")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "toor")
QUEUE_NAME = "history.graph.done"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_completion_event(message_data):
    """
    Process a completion event from agent_b_web.

    Args:
        message_data: The message data containing task completion info
    """
    logger.info("=" * 60)
    logger.info("Received completion event from agent_b_web")
    logger.info("=" * 60)

    # Extract data from message
    task_id = message_data.get("task_id")
    timestamp = message_data.get("timestamp")
    data = message_data.get("data", {})

    logger.info(f"Task ID: {task_id}")
    logger.info(f"Timestamp: {timestamp}")
    logger.info(f"Status: {data.get('status')}")
    logger.info(f"Completed At: {data.get('completed_at')}")
    logger.info(f"File Count: {data.get('file_count')}")
    logger.info(f"Collection: {data.get('collection')}")
    logger.info(f"Qdrant URL: {data.get('qdrant_url')}")

    # Your processing logic here
    # For example:
    # - Build knowledge graph
    # - Generate summaries
    # - Create visualizations
    # - Trigger additional analysis

    logger.info("Processing completed successfully")
    logger.info("=" * 60)


def on_message(channel, method, properties, body):
    """Callback for message consumption."""
    try:
        # Parse message
        message_data = json.loads(body)
        logger.info(f"Received message from queue: {QUEUE_NAME}")

        # Process the event
        process_completion_event(message_data)

        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Message acknowledged")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Negative acknowledge - requeue the message
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("History Graph Done Queue Consumer")
    logger.info("=" * 60)
    logger.info(f"RabbitMQ Host: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info("=" * 60)

    try:
        # Connect to RabbitMQ
        logger.info("Connecting to RabbitMQ...")
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare queue (idempotent)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        # Set QoS
        channel.basic_qos(prefetch_count=1)

        # Start consuming
        logger.info(f"✅ Connected. Listening for messages on queue '{QUEUE_NAME}'...")
        logger.info("Press CTRL+C to exit")
        logger.info("=" * 60)

        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=on_message
        )

        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("\nShutting down consumer...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
