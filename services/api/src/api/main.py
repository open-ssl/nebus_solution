from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from shared.config import settings

from api.api.health import router as health_router
from api.api.payments import router as payments_router
from api.core.lifespan import lifespan


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title=settings.API_TITLE,
    docs_url=settings.DOCS_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan,
)
app.include_router(payments_router)
app.include_router(health_router)


def main() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=settings.API_PORT)


if __name__ == "__main__":
    main()
