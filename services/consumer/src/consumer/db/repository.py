from __future__ import annotations

import uuid
from datetime import datetime

from shared.enums import PaymentStatus
from shared.models.payment import Payment
from sqlalchemy.ext.asyncio import AsyncSession


class PaymentRepository:
    """Status transitions for payments processed by the consumer."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def mark_processed(
        self, payment_id: uuid.UUID, status: PaymentStatus, processed_at: datetime
    ) -> Payment | None:
        """Settle a pending payment, idempotently.

        Locks the row and only transitions it when still ``pending``, so a
        redelivered message never overwrites an already-settled payment.
        """
        payment = await self.session.get(Payment, payment_id, with_for_update=True)
        if payment is None:
            return None
        if payment.status == PaymentStatus.PENDING:
            payment.status = status
            payment.processed_at = processed_at
        return payment
