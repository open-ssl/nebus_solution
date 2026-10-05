"""Domain ORM models.

Stage 2 adds the two tables required by the spec:
  - ``Payment``      (payments): amount, currency, description, metadata,
                     status, idempotency_key, webhook_url, created/processed_at.
  - ``OutboxEvent``  (outbox): transactional outbox rows published to
                     ``payments.new`` by the outbox_publisher service.

Every model must subclass ``shared.db.base.Base`` so Alembic autogenerate and
``import shared.models`` in db_migrations/env.py register its table.
"""
