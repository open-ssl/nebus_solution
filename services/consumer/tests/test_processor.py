from __future__ import annotations

import uuid
from datetime import datetime, timezone

import consumer.services.processor as processor_module
import httpx
import pytest
from consumer.services.processor import PaymentProcessor, WebhookDeliveryError
from shared.config import settings
from shared.enums import Currency, PaymentStatus
from shared.schemas import PaymentEvent


class _ACM:
    def __init__(self, obj: object) -> None:
        self._obj = obj

    async def __aenter__(self) -> object:
        return self._obj

    async def __aexit__(self, *_exc: object) -> bool:
        return False


class FakeSession:
    def begin(self) -> _ACM:
        return _ACM(self)


class FakeSessionFactory:
    def __call__(self) -> _ACM:
        return _ACM(FakeSession())


class FakePayment:
    def __init__(self, status: PaymentStatus, processed_at: object | None = None) -> None:
        self.status = status
        self.processed_at = processed_at


class FakeRepo:
    def __init__(self, session: object, store: dict) -> None:
        self._store = store

    async def get(self, pid: uuid.UUID) -> FakePayment | None:
        return self._store.get(pid)

    async def mark_processed(self, pid: uuid.UUID, status: PaymentStatus, processed_at: object) -> FakePayment | None:
        payment = self._store.get(pid)
        if payment is None:
            return None
        if payment.status == PaymentStatus.PENDING:
            payment.status = status
            payment.processed_at = processed_at
        return payment


@pytest.fixture
def fast_settings(monkeypatch):
    monkeypatch.setattr(settings, "PROCESS_MIN_SECONDS", 0.0)
    monkeypatch.setattr(settings, "PROCESS_MAX_SECONDS", 0.0)
    monkeypatch.setattr(settings, "PROCESS_SUCCESS_RATE", 1.0)
    monkeypatch.setattr(settings, "RETRY_BACKOFF_BASE_SECONDS", 0.0)
    monkeypatch.setattr(settings, "RETRY_MAX_ATTEMPTS", 3)
    return settings


def _event(pid: uuid.UUID) -> PaymentEvent:
    return PaymentEvent(payment_id=pid, amount="10.00", currency=Currency.USD, webhook_url="https://hook.test/x")


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_settles_pending_payment_and_delivers_webhook(fast_settings, monkeypatch) -> None:
    pid = uuid.uuid4()
    store = {pid: FakePayment(PaymentStatus.PENDING)}
    monkeypatch.setattr(processor_module, "PaymentRepository", lambda session: FakeRepo(session, store))

    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200)

    async with _client(handler) as client:
        await PaymentProcessor(FakeSessionFactory(), client).process(_event(pid))

    assert store[pid].status == PaymentStatus.SUCCEEDED
    assert store[pid].processed_at is not None
    assert calls["n"] == 1


async def test_already_settled_payment_is_not_resettled(fast_settings, monkeypatch) -> None:
    pid = uuid.uuid4()
    store = {pid: FakePayment(PaymentStatus.FAILED, processed_at=datetime(2026, 1, 1, tzinfo=timezone.utc))}
    monkeypatch.setattr(processor_module, "PaymentRepository", lambda session: FakeRepo(session, store))

    async with _client(lambda req: httpx.Response(200)) as client:
        await PaymentProcessor(FakeSessionFactory(), client).process(_event(pid))

    # Status unchanged (no re-charge); webhook is re-sent (at-least-once).
    assert store[pid].status == PaymentStatus.FAILED


async def test_webhook_failure_raises_after_retries_for_dlq(fast_settings, monkeypatch) -> None:
    pid = uuid.uuid4()
    store = {pid: FakePayment(PaymentStatus.PENDING)}
    monkeypatch.setattr(processor_module, "PaymentRepository", lambda session: FakeRepo(session, store))

    attempts = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(500)

    async with _client(handler) as client:
        with pytest.raises(WebhookDeliveryError):
            await PaymentProcessor(FakeSessionFactory(), client).process(_event(pid))

    assert attempts["n"] == 3  # RETRY_MAX_ATTEMPTS
    assert store[pid].status == PaymentStatus.SUCCEEDED  # processing succeeded; only delivery failed


async def test_missing_payment_is_acked_without_webhook(fast_settings, monkeypatch) -> None:
    pid = uuid.uuid4()
    monkeypatch.setattr(processor_module, "PaymentRepository", lambda session: FakeRepo(session, {}))

    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200)

    async with _client(handler) as client:
        await PaymentProcessor(FakeSessionFactory(), client).process(_event(pid))

    assert calls["n"] == 0
