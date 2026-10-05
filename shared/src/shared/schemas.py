from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from shared.enums import Currency


class PaymentEvent(BaseModel):
    """Message contract published to ``payments.new`` and consumed by the worker.

    This is the payload stored in the outbox ``payload`` column, so it must be
    JSON-serializable (Decimal is serialized as a string via ``model_dump(mode="json")``).
    """

    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str | None = None
    metadata: dict = {}
    webhook_url: str


class WebhookNotification(BaseModel):
    """Body delivered to the client's ``webhook_url`` with the final result."""

    payment_id: uuid.UUID
    status: str
    amount: Decimal
    currency: Currency
    processed_at: str | None = None
