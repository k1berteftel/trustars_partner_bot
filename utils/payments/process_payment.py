from typing import Literal
import asyncio
import logging
from asyncio import TimeoutError

from aiogram import Bot
from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from utils.payments.create_payment import check_crypto_payment, check_oxa_payment
from database.action_data_class import DataInteraction
from config_data.config import Config, load_config


logger = logging.getLogger(__name__)
config: Config = load_config()


async def wait_for_payment(
        payment_id,
        user_id: int,
        app_id: int,
        bot: Bot,
        session: DataInteraction,
        js: JetStreamContext,
        currency: int,
        rate: Literal['stars', 'premium'],
        payment_type: Literal['crypto', 'cryptoBot'],
        timeout: int = 60 * 15,
        check_interval: int = 6
):
    """
    Ожидает оплаты в фоне. Завершается при оплате или по таймауту.
    """
    try:
        await asyncio.wait_for(_poll_payment(payment_id, user_id, app_id, currency, js, bot, session, rate, payment_type, check_interval),
                               timeout=timeout)

    except TimeoutError:
        logger.warning(f"Платёж {payment_id} истёк (таймаут)")

    except Exception as e:
        logger.warning(f"Ошибка в фоновом ожидании платежа {payment_id}: {e}")


async def _poll_payment(payment_id, user_id: int, app_id: int, currency: int, js: JetStreamContext, bot: Bot, session: DataInteraction, rate: str, payment_type: str, interval: int):
    """
    Цикл опроса статуса платежа.
    Завершается, когда платёж оплачен.
    """
    while True:
        if payment_type == 'crypto':
            status = await check_oxa_payment(payment_id)
        else:
            status = await check_crypto_payment(payment_id)
        if status:
            await bot.send_message(
                chat_id=user_id,
                text='✅Оплата прошла успешно'
            )
            logger.info('execute rate')
            await execute_rate(app_id, currency, rate, payment_type, js,  bot, session)
            break
        await asyncio.sleep(interval)


async def execute_rate(app_id: int, currency: int, rate: str, payment_type: str, js: JetStreamContext, bot: Bot, session: DataInteraction):
    logger.info('open execute rate')
    logger.info(f'input data: {app_id}, {currency}, {rate}, {payment_type}')
    application = await session.get_application(app_id)
    db_bot = await session.get_bot_by_token(bot.token)
    logger.info(f'process data: {application.receiver}, {application.uid_key}')
    data = {
        'transfer_type': rate,
        'username': application.receiver,
        'currency': currency,
        'payment': payment_type,
        'app_id': application.uid_key,
        'bot_id': db_bot.id
    }
    logger.info('send data')
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )

