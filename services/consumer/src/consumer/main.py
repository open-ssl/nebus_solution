from __future__ import annotations

import asyncio
import logging

from consumer.core.app import create_app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = create_app()


def main() -> None:
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
