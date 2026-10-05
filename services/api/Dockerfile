# syntax=docker/dockerfile:1

# -----------------------------------------------------------------------------
# Stage 1: Build virtual environment with uv BuildKit cache
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 1. Install external dependencies only (cached across source changes).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=shared/pyproject.toml,target=shared/pyproject.toml \
    --mount=type=bind,source=services/api/pyproject.toml,target=services/api/pyproject.toml \
    --mount=type=bind,source=services/consumer/pyproject.toml,target=services/consumer/pyproject.toml \
    --mount=type=bind,source=services/outbox_publisher/pyproject.toml,target=services/outbox_publisher/pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace --package nb-api

# 2. Copy source and build the workspace packages into the environment.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package nb-api

# 3. Add the task runner to the venv so the container can launch via `poe`.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install poethepoet

# -----------------------------------------------------------------------------
# Stage 2: Minimal & Secure Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -u 10001 appuser

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Alembic needs its config and migration scripts at runtime (the API applies
# `alembic upgrade head` on startup before serving traffic).
COPY --chown=appuser:appgroup alembic.ini /app/alembic.ini
COPY --chown=appuser:appgroup db_migrations /app/db_migrations

# The poe task definitions live in the root pyproject; poe reads them from cwd.
COPY --chown=appuser:appgroup pyproject.toml /app/pyproject.toml

USER appuser

EXPOSE 8000
# `poe api` applies migrations, then launches uvicorn (see [tool.poe.tasks.api]).
ENTRYPOINT ["poe", "api"]
