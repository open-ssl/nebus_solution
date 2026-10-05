from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration.

    Atomic connection parameters (HOST, PORT, USER, ...) are read from the
    environment and assembled into URLs via computed fields, so there are no
    hardcoded endpoints anywhere in the codebase.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Authentication: static key expected in the X-API-Key header.
    API_KEY: str = "dev-secret-key"

    # API service
    API_PORT: int = 8000
    API_TITLE: str = "Nebus Payments API"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "nebus"
    POSTGRES_PASSWORD: str = "nebus"
    POSTGRES_DB: str = "nebus"

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # Messaging topology. The consumer binds payments.new to a retry/DLQ chain.
    PAYMENTS_EXCHANGE: str = "payments"
    PAYMENTS_NEW_QUEUE: str = "payments.new"
    PAYMENTS_DLQ: str = "payments.dlq"

    # Payment processing simulation (consumer): sleep in [min, max], succeed with rate.
    PROCESS_MIN_SECONDS: float = 2.0
    PROCESS_MAX_SECONDS: float = 5.0
    PROCESS_SUCCESS_RATE: float = 0.9

    # Retry & DLQ. Applies to webhook delivery and broker redelivery alike.
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_BASE_SECONDS: float = 2.0
    WEBHOOK_TIMEOUT_SECONDS: float = 10.0

    # Outbox relay (outbox_publisher)
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_BATCH_SIZE: int = 100

    @computed_field
    @property
    def postgres_dsn_async(self) -> str:
        """asyncpg DSN used by the services and by Alembic (async engine)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST.lstrip('/')}"
        )


settings = Settings()
