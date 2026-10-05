from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx
from shared.config import settings
from shared.enums import PaymentStatus
from shared.schemas import PaymentEvent, WebhookNotification
from sqlalchemy.ext.asyncio import async_sessionmaker
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from consumer.db.repository import PaymentRepository


logger = logging.getLogger("consumer.processor")


class WebhookDeliveryError(Exception):
    """Raised when a single webhook POST attempt fails (retryable)."""


class PaymentProcessor:
    """Simulates gateway processing, settles the payment, delivers the webhook."""

    def __init__(self, session_factory: async_sessionmaker, http_client: httpx.AsyncClient) -> None:
        self._session_factory = session_factory
        self._http = http_client

    async def process(self, event: PaymentEvent) -> None:
        """Process one payment message end to end.

        Raises WebhookDeliveryError if the webhook cannot be delivered after
        RETRY_MAX_ATTEMPTS — the caller rejects the message so the broker
        dead-letters it to payments.dlq.
        """
        status, processed_at = await self._settle(event)
        if status is None:
            logger.warning("payment %s not found; acking without action", event.payment_id)
            return
        await self._deliver_webhook(event, status, processed_at)

    async def _settle(self, event: PaymentEvent) -> tuple[PaymentStatus | None, datetime | None]:
        # Idempotency fast-path: a redelivered message skips the simulation and
        # reuses the already-settled result (we still re-send the webhook).
        async with self._session_factory() as session:
            payment = await PaymentRepository(session).get(event.payment_id)
            if payment is None:
                return None, None
            if payment.status != PaymentStatus.PENDING:
                return payment.status, payment.processed_at

        # Emulate the external gateway: 2-5s latency, PROCESS_SUCCESS_RATE success.
        await asyncio.sleep(random.uniform(settings.PROCESS_MIN_SECONDS, settings.PROCESS_MAX_SECONDS))
        outcome = PaymentStatus.SUCCEEDED if random.random() < settings.PROCESS_SUCCESS_RATE else PaymentStatus.FAILED
        processed_at = datetime.now(timezone.utc)

        async with self._session_factory() as session, session.begin():
            payment = await PaymentRepository(session).mark_processed(event.payment_id, outcome, processed_at)
            if payment is None:
                return None, None
            status, processed_at = payment.status, payment.processed_at
        logger.info("payment %s settled: %s", event.payment_id, status)
        return status, processed_at

    async def _deliver_webhook(self, event: PaymentEvent, status: PaymentStatus, processed_at: datetime | None) -> None:
        payload = WebhookNotification(
            payment_id=event.payment_id,
            status=status,
            amount=event.amount,
            currency=event.currency,
            processed_at=processed_at.isoformat() if processed_at else None,
        ).model_dump(mode="json")

        # RETRY_MAX_ATTEMPTS attempts with exponential backoff (tenacity);
        # reraise the last error so process() can route the message to the DLQ.
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=settings.RETRY_BACKOFF_BASE_SECONDS),
            retry=retry_if_exception_type(WebhookDeliveryError),
            reraise=True,
        ):
            with attempt:
                await self._post_once(event, payload)

    async def _post_once(self, event: PaymentEvent, payload: dict) -> None:
        try:
            response = await self._http.post(event.webhook_url, json=payload, timeout=settings.WEBHOOK_TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("webhook %s delivery attempt failed: %s", event.payment_id, error)
            raise WebhookDeliveryError(str(error)) from error
        logger.info("webhook %s delivered (%s)", event.payment_id, response.status_code)
