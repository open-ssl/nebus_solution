from __future__ import annotations

import uuid

import pytest
from api.schemas import PaymentCreate
from api.services.payment_service import PaymentService
from shared.enums import Currency, PaymentStatus
from shared.models.payment import Payment
from sqlalchemy.exc import IntegrityError


def _body() -> PaymentCreate:
    return PaymentCreate(
        amount="199.99",
        currency=Currency.RUB,
        description="Order #1",
        metadata={"order_id": 1},
        webhook_url="https://example.com/hook",
    )


class FakeRepo:
    """In-memory stand-in for PaymentRepository (no DB)."""

    def __init__(self, *, existing: Payment | None = None, raise_integrity: bool = False) -> None:
        self.session = type("S", (), {"rollback": _noop_async})()
        self._by_key: dict[str, Payment] = {}
        if existing is not None:
            self._by_key[existing.idempotency_key] = existing
        self._raise_integrity = raise_integrity
        self.created: list[tuple[Payment, object]] = []

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return self._by_key.get(key)

    async def create_with_outbox(self, payment: Payment, event: object) -> Payment:
        if self._raise_integrity:
            # Simulate a concurrent insert winning the unique key, then the race.
            self._by_key[payment.idempotency_key] = _winner(payment.idempotency_key)
            raise IntegrityError("insert", {}, Exception("duplicate key"))
        self._by_key[payment.idempotency_key] = payment
        self.created.append((payment, event))
        return payment


async def _noop_async(*_args, **_kwargs) -> None:
    return None


def _winner(key: str) -> Payment:
    return Payment(
        id=uuid.uuid4(),
        amount=1,
        currency=Currency.RUB,
        extra_metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key=key,
        webhook_url="https://example.com/hook",
    )


def _service_with(repo: FakeRepo) -> PaymentService:
    svc = PaymentService.__new__(PaymentService)
    svc.repo = repo
    return svc


async def test_create_persists_payment_and_outbox() -> None:
    repo = FakeRepo()
    svc = _service_with(repo)
    payment = await svc.create(_body(), "idem-1")
    assert payment.status == PaymentStatus.PENDING
    assert payment.idempotency_key == "idem-1"
    assert len(repo.created) == 1
    _, event = repo.created[0]
    assert event.event_type  # outbox event written alongside
    assert event.payload["currency"] == "RUB"


async def test_replay_returns_existing_without_creating() -> None:
    existing = _winner("idem-1")
    repo = FakeRepo(existing=existing)
    svc = _service_with(repo)
    payment = await svc.create(_body(), "idem-1")
    assert payment is existing
    assert repo.created == []


async def test_race_on_unique_key_resolves_to_winner() -> None:
    repo = FakeRepo(raise_integrity=True)
    svc = _service_with(repo)
    payment = await svc.create(_body(), "idem-1")
    assert payment.idempotency_key == "idem-1"
    assert repo.created == []  # our insert lost the race


@pytest.mark.parametrize("bad_amount", ["0", "-1", "1.234"])
def test_payment_create_rejects_invalid_amount(bad_amount: str) -> None:
    with pytest.raises(ValueError):
        PaymentCreate(amount=bad_amount, currency=Currency.USD, webhook_url="https://e.com/h")
