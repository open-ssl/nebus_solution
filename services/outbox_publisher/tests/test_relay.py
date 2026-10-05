from __future__ import annotations

import outbox_publisher.services.relay as relay_module
from outbox_publisher.services.relay import OutboxRelay
from shared.broker import payments_exchange


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


class FakeEvent:
    def __init__(self, payload: dict, event_type: str) -> None:
        self.payload = payload
        self.event_type = event_type
        self.published_at: object | None = None


class FakeBroker:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, message: dict, *, exchange: object, routing_key: str) -> None:
        assert exchange is payments_exchange
        self.published.append((routing_key, message))


class FakeRepo:
    def __init__(self, events: list[FakeEvent]) -> None:
        self._events = events
        self.marked: list[FakeEvent] = []

    def __call__(self, _session: object) -> "FakeRepo":
        return self

    async def fetch_unpublished(self, _limit: int) -> list[FakeEvent]:
        return self._events

    def mark_published(self, event: FakeEvent) -> None:
        self.marked.append(event)


async def test_drain_once_publishes_each_event_and_marks_them(monkeypatch) -> None:
    events = [FakeEvent({"payment_id": "a"}, "payments.new"), FakeEvent({"payment_id": "b"}, "payments.new")]
    repo = FakeRepo(events)
    monkeypatch.setattr(relay_module, "OutboxRepository", repo)

    broker = FakeBroker()
    relay = OutboxRelay(broker, FakeSessionFactory())
    count = await relay.drain_once()

    assert count == 2
    assert broker.published == [("payments.new", {"payment_id": "a"}), ("payments.new", {"payment_id": "b"})]
    assert repo.marked == events


async def test_drain_once_empty_returns_zero(monkeypatch) -> None:
    repo = FakeRepo([])
    monkeypatch.setattr(relay_module, "OutboxRepository", repo)
    broker = FakeBroker()
    relay = OutboxRelay(broker, FakeSessionFactory())
    assert await relay.drain_once() == 0
    assert broker.published == []
