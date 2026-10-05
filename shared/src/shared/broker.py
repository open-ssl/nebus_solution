"""RabbitMQ topology shared by the publisher and the consumer.

A single source of truth for the exchanges and queues so both services declare
exactly the same objects (names, durability, and the retry/DLQ arguments).

Topology:

    payments (direct) --payments.new--> payments.new queue
                                             │ on reject/nack (requeue=False)
                                             ▼  x-dead-letter-exchange
    payments.dlx (direct) --payments.dlq--> payments.dlq queue

The consumer rejects a message (without requeue) once webhook delivery has
exhausted its retries, so the broker dead-letters it straight to payments.dlq.
"""

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from shared.config import settings


payments_exchange = RabbitExchange(
    settings.PAYMENTS_EXCHANGE,
    type=ExchangeType.DIRECT,
    durable=True,
)

dlx_exchange = RabbitExchange(
    f"{settings.PAYMENTS_EXCHANGE}.dlx",
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_new_queue = RabbitQueue(
    settings.PAYMENTS_NEW_QUEUE,
    durable=True,
    routing_key=settings.PAYMENTS_NEW_QUEUE,
    arguments={
        "x-dead-letter-exchange": dlx_exchange.name,
        "x-dead-letter-routing-key": settings.PAYMENTS_DLQ,
    },
)

payments_dlq = RabbitQueue(
    settings.PAYMENTS_DLQ,
    durable=True,
    routing_key=settings.PAYMENTS_DLQ,
)


async def declare_topology(broker: RabbitBroker) -> None:
    """Declare exchanges, queues, and their bindings.

    The bindings must exist independently of the consumer: the relay publishes
    to the ``payments`` exchange, so without an exchange->queue binding in place
    the broker would discard events whenever the consumer is not yet up.
    """
    exchange = await broker.declare_exchange(payments_exchange)
    dlx = await broker.declare_exchange(dlx_exchange)
    new_queue = await broker.declare_queue(payments_new_queue)
    dlq = await broker.declare_queue(payments_dlq)

    await new_queue.bind(exchange, routing_key=settings.PAYMENTS_NEW_QUEUE)
    await dlq.bind(dlx, routing_key=settings.PAYMENTS_DLQ)
