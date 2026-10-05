from shared.config import Settings


def test_postgres_dsn_is_async_and_composed_from_parts() -> None:
    s = Settings(
        POSTGRES_USER="u",
        POSTGRES_PASSWORD="p",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5433,
        POSTGRES_DB="payments",
    )
    assert s.postgres_dsn_async == "postgresql+asyncpg://u:p@db:5433/payments"


def test_rabbitmq_url_strips_leading_slash_from_vhost() -> None:
    s = Settings(
        RABBITMQ_USER="guest",
        RABBITMQ_PASSWORD="guest",
        RABBITMQ_HOST="mq",
        RABBITMQ_PORT=5672,
        RABBITMQ_VHOST="/",
    )
    assert s.rabbitmq_url == "amqp://guest:guest@mq:5672/"


def test_retry_defaults_match_spec() -> None:
    s = Settings()
    assert s.RETRY_MAX_ATTEMPTS == 3
    assert s.PROCESS_SUCCESS_RATE == 0.9
