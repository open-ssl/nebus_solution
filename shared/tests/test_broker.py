from shared.broker import dlx_exchange, payments_dlq, payments_exchange, payments_new_queue
from shared.config import settings


def test_payments_new_queue_dead_letters_to_dlx() -> None:
    args = payments_new_queue.arguments
    assert args["x-dead-letter-exchange"] == dlx_exchange.name
    assert args["x-dead-letter-routing-key"] == settings.PAYMENTS_DLQ


def test_topology_names_and_durability() -> None:
    assert payments_exchange.name == settings.PAYMENTS_EXCHANGE
    assert payments_new_queue.name == settings.PAYMENTS_NEW_QUEUE
    assert payments_dlq.name == settings.PAYMENTS_DLQ
    assert payments_exchange.durable
    assert payments_new_queue.durable
    assert payments_dlq.durable
