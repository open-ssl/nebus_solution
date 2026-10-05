from __future__ import annotations

import logging

from faststream.rabbit import RabbitBroker
from shared.broker import payments_exchange
from shared.config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker

from outbox_publisher.db.repository import OutboxRepository


logger = logging.getLogger("outbox_publisher.relay")


class OutboxRelay:
    """Relays unpublished outbox rows to RabbitMQ, one batch per poll."""

    def __init__(self, broker: RabbitBroker, session_factory: async_sessionmaker) -> None:
        self._broker = broker
        self._session_factory = session_factory

    async def drain_once(self) -> int:
        """Publish one batch of unpublished events; return how many were sent.

        Fetch, publish, and mark-published run inside a single DB transaction so
        the row lock (``FOR UPDATE SKIP LOCKED``) is held until the rows are
        stamped. Publishing is at-least-once: if the commit fails after a
        successful publish the event is re-sent on the next poll, and the
        consumer is idempotent, so no event is ever lost or double-processed.
        """
        async with self._session_factory() as session, session.begin():
            repo = OutboxRepository(session)
            events = await repo.fetch_unpublished(settings.OUTBOX_BATCH_SIZE)
            for event in events:
                await self._broker.publish(
                    event.payload,
                    exchange=payments_exchange,
                    routing_key=event.event_type,
                )
                repo.mark_published(event)
        if events:
            logger.info("published %d outbox event(s)", len(events))
        return len(events)
