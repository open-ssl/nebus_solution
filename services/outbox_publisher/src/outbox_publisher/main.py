from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from shared.config import settings
from shared.db.session import engine, session_factory

from outbox_publisher.core.broker import connect
from outbox_publisher.services.relay import OutboxRelay


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("outbox_publisher")


async def run() -> None:
    logger.info(
        "outbox_publisher starting (poll=%.1fs, batch=%d)",
        settings.OUTBOX_POLL_INTERVAL_SECONDS,
        settings.OUTBOX_BATCH_SIZE,
    )
    broker = await connect(settings.rabbitmq_url)
    relay = OutboxRelay(broker, session_factory)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    try:
        while not stop.is_set():
            try:
                published = await relay.drain_once()
            except Exception:
                logger.exception("outbox poll failed; retrying after interval")
                published = 0
            # Back off only when idle; keep draining while there is a backlog.
            if published == 0:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=settings.OUTBOX_POLL_INTERVAL_SECONDS)
    finally:
        logger.info("outbox_publisher shutting down")
        await broker.close()
        await engine.dispose()
        logger.info("outbox_publisher stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
