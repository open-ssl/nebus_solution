from __future__ import annotations

import uuid

from shared.config import settings
from shared.enums import PaymentStatus
from shared.models.outbox import OutboxEvent
from shared.models.payment import Payment
from shared.schemas import PaymentEvent
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.repository import PaymentRepository
from api.schemas import PaymentCreate


class PaymentService:
    """Orchestrates payment creation with idempotency and the outbox write."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = PaymentRepository(session)

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.repo.get_by_id(payment_id)

    async def create(self, data: PaymentCreate, idempotency_key: str) -> Payment:
        """Create a pending payment and its outbox event, idempotently.

        Replaying the same Idempotency-Key returns the original payment instead
        of creating a duplicate. A concurrent duplicate is caught at the unique
        constraint and resolved to the winning row.
        """
        existing = await self.repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        payment_id = uuid.uuid4()
        payment = Payment(
            id=payment_id,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            extra_metadata=data.metadata,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            webhook_url=str(data.webhook_url),
        )
        event = OutboxEvent(
            aggregate_id=payment_id,
            event_type=settings.PAYMENTS_NEW_QUEUE,
            payload=PaymentEvent(
                payment_id=payment_id,
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                metadata=data.metadata,
                webhook_url=str(data.webhook_url),
            ).model_dump(mode="json"),
        )

        try:
            return await self.repo.create_with_outbox(payment, event)
        except IntegrityError:
            # Lost a race on the unique idempotency_key — return the winner.
            await self.repo.session.rollback()
            winner = await self.repo.get_by_idempotency_key(idempotency_key)
            if winner is None:
                raise
            return winner
