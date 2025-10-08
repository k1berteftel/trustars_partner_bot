import json
import logging

from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)


async def send_publisher_data(
    js: JetStreamContext,
    subject: str,
    data: dict
) -> None:
    logger.info('start_transfer')
    await js.publish(subject=subject, payload=json.dumps(data).encode())