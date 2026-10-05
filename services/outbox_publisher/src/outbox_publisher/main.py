from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from shared.config import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("outbox_publisher")


async def run() -> None:
    logger.info(
        "outbox_publisher starting (poll=%.1fs, batch=%d)",
        settings.OUTBOX_POLL_INTERVAL_SECONDS,
        settings.OUTBOX_BATCH_SIZE,
    )

    # Stage 4: connect to Postgres + RabbitMQ, then loop:
    #   1. SELECT ... FROM outbox WHERE published_at IS NULL
    #      ORDER BY created_at LIMIT OUTBOX_BATCH_SIZE FOR UPDATE SKIP LOCKED
    #   2. publish each event to the payments exchange -> PAYMENTS_NEW_QUEUE
    #   3. mark the row published (published_at = now()) in the same transaction
    #   sleep OUTBOX_POLL_INTERVAL_SECONDS between empty polls.

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    logger.info("outbox_publisher stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
