from __future__ import annotations

import asyncio
import logging

from faststream.rabbit import RabbitBroker
from shared.broker import dlx_exchange, payments_dlq, payments_exchange, payments_new_queue


logger = logging.getLogger("outbox_publisher.broker")


async def connect(url: str, *, retries: int = 10, delay: float = 1.0) -> RabbitBroker:
    """Connect to RabbitMQ (with startup retries) and declare the topology.

    Declaring the exchanges and queues here means the relay provisions them on
    first start, independent of consumer startup order.
    """
    broker = RabbitBroker(url)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            await broker.connect()
            await broker.declare_exchange(payments_exchange)
            await broker.declare_exchange(dlx_exchange)
            await broker.declare_queue(payments_new_queue)
            await broker.declare_queue(payments_dlq)
            logger.info("connected to RabbitMQ and declared payments topology")
            return broker
        except Exception as error:  # noqa: BLE001
            last_error = error
            logger.warning("RabbitMQ not ready (attempt %d/%d): %s", attempt, retries, error)
            await asyncio.sleep(delay)
    raise RuntimeError("could not connect to RabbitMQ") from last_error
