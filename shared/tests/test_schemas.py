import uuid
from decimal import Decimal

from shared.enums import Currency
from shared.schemas import PaymentEvent, WebhookNotification


def test_payment_event_json_mode_serializes_decimal_and_uuid_as_strings() -> None:
    pid = uuid.uuid4()
    event = PaymentEvent(
        payment_id=pid,
        amount=Decimal("199.99"),
        currency=Currency.RUB,
        description="Order #1",
        metadata={"order_id": 1},
        webhook_url="https://example.com/hook",
    )
    dumped = event.model_dump(mode="json")
    assert dumped["payment_id"] == str(pid)
    assert dumped["amount"] == "199.99"
    assert dumped["currency"] == "RUB"
    assert dumped["metadata"] == {"order_id": 1}


def test_payment_event_roundtrips_through_json() -> None:
    event = PaymentEvent(
        payment_id=uuid.uuid4(),
        amount=Decimal("10.00"),
        currency=Currency.USD,
        webhook_url="https://e.com/h",
    )
    restored = PaymentEvent.model_validate(event.model_dump(mode="json"))
    assert restored == event


def test_webhook_notification_shape() -> None:
    note = WebhookNotification(
        payment_id=uuid.uuid4(),
        status="succeeded",
        amount=Decimal("5.50"),
        currency=Currency.EUR,
        processed_at="2026-10-05T10:00:00+00:00",
    )
    dumped = note.model_dump(mode="json")
    assert dumped["status"] == "succeeded"
    assert dumped["amount"] == "5.50"
    assert dumped["currency"] == "EUR"
