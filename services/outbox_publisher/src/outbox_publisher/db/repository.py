from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from shared.models.outbox import OutboxEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class OutboxRepository:
    """Reads and claims unpublished outbox rows for the relay."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch_unpublished(self, limit: int) -> Sequence[OutboxEvent]:
        """Claim up to ``limit`` unpublished rows for this transaction.

        ``FOR UPDATE SKIP LOCKED`` lets multiple relay instances run
        concurrently without processing the same row twice: locked rows are
        simply skipped instead of blocking.
        """
        result = await self.session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.scalars().all()

    @staticmethod
    def mark_published(event: OutboxEvent) -> None:
        event.published_at = datetime.now(timezone.utc)
