from __future__ import annotations

import logging

import httpx
from faststream import FastStream
from faststream.exceptions import RejectMessage
from faststream.rabbit import RabbitBroker, RabbitMessage
from shared.broker import dlx_exchange, payments_dlq, payments_exchange, payments_new_queue
from shared.config import settings
from shared.db.session import engine, session_factory
from shared.schemas import PaymentEvent

from consumer.services.processor import PaymentProcessor, WebhookDeliveryError


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("consumer")

broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)


class _Runtime:
    """Holds the shared HTTP client + processor, wired once on startup."""

    http_client: httpx.AsyncClient | None = None
    processor: PaymentProcessor | None = None


runtime = _Runtime()


@app.after_startup
async def on_startup() -> None:
    # Ensure the dead-letter side of the topology exists so rejected messages
    # are actually routed to payments.dlq (a missing DLX silently drops them).
    await broker.declare_exchange(dlx_exchange)
    await broker.declare_queue(payments_dlq)

    runtime.http_client = httpx.AsyncClient()
    runtime.processor = PaymentProcessor(session_factory, runtime.http_client)
    logger.info("consumer ready, consuming %s", settings.PAYMENTS_NEW_QUEUE)


@app.on_shutdown
async def on_shutdown() -> None:
    if runtime.http_client is not None:
        await runtime.http_client.aclose()
    await engine.dispose()
    logger.info("consumer stopped")


@broker.subscriber(payments_new_queue, payments_exchange)
async def process_payment(event: PaymentEvent, message: RabbitMessage) -> None:
    assert runtime.processor is not None  # set in after_startup
    try:
        await runtime.processor.process(event)
    except WebhookDeliveryError:
        logger.error(
            "payment %s: webhook delivery exhausted after %d attempts -> DLQ",
            event.payment_id,
            settings.RETRY_MAX_ATTEMPTS,
        )
        # Reject without requeue: the broker dead-letters the message to payments.dlq.
        raise RejectMessage() from None


@broker.subscriber(payments_dlq)
async def observe_dead_letters(message: RabbitMessage) -> None:
    logger.error("dead-lettered payment message: %s", message.body)


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
