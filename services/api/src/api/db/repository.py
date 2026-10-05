from __future__ import annotations

import uuid

from shared.models.outbox import OutboxEvent
from shared.models.payment import Payment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PaymentRepository:
    """SQL/ORM access for payments and their outbox events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create_with_outbox(self, payment: Payment, event: OutboxEvent) -> Payment:
        """Persist the payment and its outbox event in a single transaction.

        This atomicity is the core of the transactional outbox pattern: either
        both rows commit or neither does, so a published event can never exist
        without its payment (and vice versa).
        """
        self.session.add(payment)
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment
