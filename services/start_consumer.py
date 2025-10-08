import logging

from sqlalchemy.ext.asyncio import async_sessionmaker
from services.consumer import TransactionConsumer

from nats.aio.client import Client
from nats.js.client import JetStreamContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


async def start_transfer_consumer(
    nc: Client,
    js: JetStreamContext,
    sessions: async_sessionmaker,
    scheduler: AsyncIOScheduler,
    subject: str,
    stream: str,
    durable_name: str
) -> None:
    consumer = TransactionConsumer(
        nc=nc,
        js=js,
        sessions=sessions,
        scheduler=scheduler,
        subject=subject,
        stream=stream,
        durable_name=durable_name
    )
    logger.info('Start transactions consumer')
    await consumer.start()