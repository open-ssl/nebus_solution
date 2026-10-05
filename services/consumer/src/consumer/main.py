from __future__ import annotations

import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from shared.config import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("consumer")

broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)


@app.after_startup
async def on_startup() -> None:
    logger.info("consumer started, waiting for %s", settings.PAYMENTS_NEW_QUEUE)


# Stage 4: declare the payments exchange + payments.new queue bound to a retry/DLQ
#          chain (x-dead-letter-exchange), subscribe here, then on each message:
#            1. simulate processing (sleep 2-5s, succeed with PROCESS_SUCCESS_RATE)
#            2. update the payment status (succeeded/failed) + processed_at in Postgres
#            3. deliver the webhook with RETRY_MAX_ATTEMPTS exponential retries (tenacity)
#          Messages still failing after RETRY_MAX_ATTEMPTS land in PAYMENTS_DLQ.


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
