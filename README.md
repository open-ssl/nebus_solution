# Nebus — Async Payment Processing Service

Asynchronous payment-processing microservice. The API accepts payment requests,
a worker processes them through an emulated payment gateway, and the client is
notified of the result via webhook. Delivery guarantees are provided by the
**transactional outbox pattern**, **idempotency keys**, **retries with
exponential backoff**, and a **Dead Letter Queue**.

> **Status:** feature-complete. All eight deliverables are implemented and the
> full flow is verified end to end under Docker Compose (create → outbox →
> relay → consume → settle → webhook, with retries and DLQ).

## Architecture

```
            POST /api/v1/payments (X-API-Key, Idempotency-Key)
                        │
                        ▼
                 ┌─────────────┐     one DB transaction
                 │     api     │  payments(pending) + outbox row
                 │  (FastAPI)  │
                 └──────┬──────┘
                        │ writes
                        ▼
                 ┌─────────────┐
                 │  PostgreSQL │◄────────────────────────────┐
                 └──────┬──────┘                             │ status update
                        │ polls unpublished outbox rows      │
                        ▼                                     │
               ┌──────────────────┐   payments.new    ┌──────┴──────┐
               │ outbox_publisher │ ───────────────►  │   consumer  │
               │  (outbox relay)  │     RabbitMQ      │ (FastStream)│
               └──────────────────┘                   └──────┬──────┘
                                                             │ webhook (retry ×3)
                        retry/DLQ chain                      ▼
                        payments.dlq                    client webhook_url
```

- **api** (FastAPI + Pydantic v2) — `POST /api/v1/payments`, `GET /api/v1/payments/{id}`.
  Creates the payment and an outbox row in a single transaction, returns `202 Accepted`.
- **outbox_publisher** — polls the `outbox` table and publishes events to the
  `payments` exchange / `payments.new` queue, then marks rows as published.
- **consumer** (FastStream RabbitMQ) — simulates processing (2–5 s, 90 % success),
  updates payment status, delivers the webhook with 3 exponential retries, and
  routes finally-failed messages to the Dead Letter Queue.
- **postgres**, **rabbitmq** — infrastructure.

### Stack

FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · asyncpg · PostgreSQL ·
RabbitMQ (FastStream) · Alembic · Docker Compose · `uv` workspace monorepo.

## Repository layout

```
nebus_solution/
├── pyproject.toml            # uv workspace, ruff, pytest, poe tasks
├── alembic.ini               # Alembic config (DSN injected from shared.config)
├── db_migrations/            # env.py (async), script.py.mako, versions/
├── docker-compose.yml        # postgres, rabbitmq, api, consumer, outbox_publisher
├── shared/                   # nb-shared: config, db base/session, models
└── services/
    ├── api/                  # nb-api (FastAPI)
    ├── consumer/             # nb-consumer (FastStream worker)
    └── outbox_publisher/     # nb-outbox-publisher (outbox relay)
```

Each Python service follows a layered layout inside `src/<name>/`: `api/`
(routers), `core/` (clients, app wiring), `db/` (repositories), `services/`
(business logic), `main.py` (assembly point only).

## Quick start

```bash
cp .env.example .env          # adjust secrets as needed
make run                      # build + start the whole stack (detached)
make logs                     # follow logs
make down                     # stop everything
```

The API is served on `http://localhost:8000` (Swagger UI at `/docs`).
RabbitMQ management UI: `http://localhost:15672` (guest/guest by default).
Migrations are applied automatically by the `api` container on startup
(`alembic upgrade head`).

### Local development

```bash
make open_project             # uv sync --all-packages
make migrate                  # apply migrations against the DB in .env
make test                     # pytest + coverage
make lint                     # ruff check + format (installs pre-commit hook)
```

## API

All endpoints require the `X-API-Key` header (value from `API_KEY`).

### Create a payment

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: dev-secret-key" \
  -H "Idempotency-Key: 7c1f8e2a-..." \
  -H "Content-Type: application/json" \
  -d '{
        "amount": "199.99",
        "currency": "RUB",
        "description": "Order #123",
        "metadata": {"order_id": 123},
        "webhook_url": "https://example.com/webhooks/payments"
      }'
```

Response `202 Accepted`:

```json
{ "payment_id": "…", "status": "pending", "created_at": "…" }
```

Re-sending the same `Idempotency-Key` returns the original payment instead of
creating a duplicate.

### Get a payment

```bash
curl http://localhost:8000/api/v1/payments/{payment_id} \
  -H "X-API-Key: dev-secret-key"
```

## Configuration

All configuration comes from environment variables (see `.env.example`).
Connection parameters are atomic (`*_HOST`, `*_PORT`, …) and assembled into URLs
via Pydantic computed fields — no hardcoded endpoints. Key knobs: `API_KEY`,
`RETRY_MAX_ATTEMPTS` (3), `RETRY_BACKOFF_BASE_SECONDS`, `PROCESS_SUCCESS_RATE`
(0.9), `OUTBOX_POLL_INTERVAL_SECONDS`.

## Deliverables

All eight requirements from the brief are implemented:

1. ✅ **Models & migrations** — `Payment` + `OutboxEvent`, initial Alembic revision.
2. ✅ **API** — Pydantic v2 schemas, `X-API-Key` auth, `POST` (202) / `GET`, idempotency.
3. ✅ **Consumer** — one handler: simulate → update status → deliver webhook.
4. ✅ **Outbox pattern** — atomic payment+event write, relay with `FOR UPDATE SKIP LOCKED`.
5. ✅ **Retry** — 3 webhook attempts with exponential backoff (tenacity).
6. ✅ **Dead Letter Queue** — `payments.new` → DLX → `payments.dlq` after exhausted retries.
7. ✅ **Docker** — Compose with postgres, rabbitmq, api, consumer (+ outbox_publisher).
8. ✅ **Documentation** — this README (run instructions and examples).

## Testing

Hermetic unit tests (no live Postgres/RabbitMQ — fakes, `monkeypatch`, httpx
`MockTransport`) cover config, schemas, topology, API auth/service/idempotency,
the outbox relay, and the consumer's settle/retry/DLQ logic. Run `make test`.
