from __future__ import annotations

import asyncio
import logging

from outbox_publisher.core.runner import run


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
