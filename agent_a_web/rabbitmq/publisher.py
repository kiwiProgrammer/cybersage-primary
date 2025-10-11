"""RabbitMQ publisher for publishing messages to queues."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pika

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """RabbitMQ publisher for sending messages to queues."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize RabbitMQ publisher.

        Args:
            host: RabbitMQ host (default: from env RABBITMQ_HOST or 'rabbitmq')
            port: RabbitMQ port (default: from env RABBITMQ_PORT or 5672)
            username: RabbitMQ username (default: from env RABBITMQ_USER or 'root')
            password: RabbitMQ password (default: from env RABBITMQ_PASS or 'toor')
        """
        self.host = host or os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.port = port or int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = username or os.getenv("RABBITMQ_USER", "root")
        self.password = password or os.getenv("RABBITMQ_PASS", "toor")

    def _get_connection(self) -> pika.BlockingConnection:
        """
        Create and return a RabbitMQ connection.

        Returns:
            pika.BlockingConnection: The RabbitMQ connection

        Raises:
            Exception: If connection fails
        """
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials
        )
        return pika.BlockingConnection(parameters)

    def publish(
        self,
        queue_name: str,
        message: Dict[str, Any],
        durable: bool = True,
        persistent: bool = True
    ) -> bool:
        """
        Publish a message to a RabbitMQ queue.

        Args:
            queue_name: Name of the queue to publish to
            message: Dictionary message to publish (will be JSON serialized)
            durable: Whether the queue should be durable (default: True)
            persistent: Whether messages should persist (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        connection = None
        try:
            # Connect to RabbitMQ
            connection = self._get_connection()
            channel = connection.channel()

            # Declare queue (idempotent - will create if not exists)
            channel.queue_declare(queue=queue_name, durable=durable)

            # Prepare message body
            body = json.dumps(message)

            # Publish message
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2 if persistent else 1,  # 2 = persistent
                    content_type='application/json'
                )
            )

            logger.info(f"Published message to queue '{queue_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ queue '{queue_name}': {e}", exc_info=True)
            return False

        finally:
            if connection and not connection.is_closed:
                connection.close()

    def publish_with_timestamp(
        self,
        queue_name: str,
        data: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> bool:
        """
        Publish a message with automatic timestamp and optional task_id.

        Args:
            queue_name: Name of the queue to publish to
            data: Data dictionary to publish
            task_id: Optional task ID to include in the message

        Returns:
            bool: True if successful, False otherwise
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        if task_id:
            message["task_id"] = task_id

        return self.publish(queue_name, message)


def publish_message(
    queue_name: str,
    message: Dict[str, Any],
    task_id: Optional[str] = None,
    add_timestamp: bool = True
) -> bool:
    """
    Convenience function to publish a message to RabbitMQ.

    Args:
        queue_name: Name of the queue to publish to
        message: Message dictionary to publish
        task_id: Optional task ID to include
        add_timestamp: Whether to add timestamp automatically (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    publisher = RabbitMQPublisher()

    if add_timestamp:
        return publisher.publish_with_timestamp(queue_name, message, task_id)
    else:
        return publisher.publish(queue_name, message)
