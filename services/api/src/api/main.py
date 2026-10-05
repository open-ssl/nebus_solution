from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from shared.config import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("api")

app = FastAPI(title=settings.API_TITLE, docs_url=settings.DOCS_URL, openapi_url=settings.OPENAPI_URL)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Stage 2: X-API-Key auth dependency (shared), Pydantic v2 request/response schemas.
# Stage 3: POST /api/v1/payments  — Idempotency-Key header; within one DB transaction
#          insert the Payment (status=pending) and an OutboxEvent row, then return 202.
# Stage 3: GET  /api/v1/payments/{payment_id} — detailed payment info.


def main() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=settings.API_PORT)


if __name__ == "__main__":
    main()
