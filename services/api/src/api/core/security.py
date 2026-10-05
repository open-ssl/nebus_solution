from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from shared.config import settings


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Depends(_api_key_header)) -> None:
    """Reject requests without a valid static X-API-Key header.

    Uses a constant-time comparison to avoid leaking the key via timing.
    """
    if api_key is None or not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
