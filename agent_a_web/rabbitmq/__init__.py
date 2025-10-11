"""RabbitMQ messaging package for agent services."""

from .publisher import RabbitMQPublisher, publish_message

__all__ = ["RabbitMQPublisher", "publish_message"]
