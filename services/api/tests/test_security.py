import pytest
from api.core.security import require_api_key
from fastapi import HTTPException
from shared.config import settings


async def test_accepts_valid_key() -> None:
    await require_api_key(settings.API_KEY)  # does not raise


async def test_rejects_missing_key() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_api_key(None)
    assert exc.value.status_code == 401


async def test_rejects_wrong_key() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_api_key("not-the-key")
    assert exc.value.status_code == 401
