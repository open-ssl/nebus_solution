"""Alembic environment.

Async migrations driven by the same asyncpg DSN the services use, so there is a
single Postgres driver across the whole project. The target metadata is the
shared ``Base`` — every model that subclasses it is picked up for autogenerate.
"""

import asyncio
from logging.config import fileConfig

import shared.models  # noqa: F401  (registers every table on Base.metadata)
from alembic import context
from shared.config import settings
from shared.db.base import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime DSN (asyncpg) built from environment-driven settings.
config.set_main_option("sqlalchemy.url", settings.postgres_dsn_async)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode against an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
