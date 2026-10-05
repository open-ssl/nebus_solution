from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.db.session import engine


logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("api starting")
    yield
    await engine.dispose()
    logger.info("api stopped")
