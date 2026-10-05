from __future__ import annotations

import httpx

from consumer.services.processor import PaymentProcessor


class Runtime:
    """Holds the shared HTTP client + processor, wired once on startup."""

    http_client: httpx.AsyncClient | None = None
    processor: PaymentProcessor | None = None
