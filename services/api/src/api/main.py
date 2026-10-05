from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from shared.config import settings
from shared.db.session import engine

from api.api.payments import router as payments_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("api starting")
    yield
    await engine.dispose()
    logger.info("api stopped")


app = FastAPI(
    title=settings.API_TITLE,
    docs_url=settings.DOCS_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan,
)
app.include_router(payments_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=settings.API_PORT)


if __name__ == "__main__":
    main()
