import random
import asyncio
import datetime
from typing import Literal
from cachetools import TTLCache

from aiogram import Bot
from aiohttp import ClientSession
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Form, status, Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.action_data_class import DataInteraction
from utils.payments.create_payment import (get_oxa_payment_data, get_crypto_payment_data, _get_usdt_rub,
                                           check_crypto_payment, check_oxa_payment, _get_signature)
from utils.schedulers import check_sub
from config_data.config import Config, load_config


config: Config = load_config()


webapp_router = APIRouter()


rates = {
    'standart': 15,
    'full': 30
}

ALLOWED_IPS: list[str] = [
    "168.119.157.136",
    "168.119.60.227",
    "178.154.197.79",
    "51.250.54.238"
]


order_storage = TTLCache(
    maxsize=1000,
    ttl=60 * 60 * 3
)


class PaymentMethod(BaseModel):
    id: str
    url: str
    name: str
    icon: str


class PaymentResponse(BaseModel):
    id: int
    amount: int
    rate: str
    payments: list[PaymentMethod]


class StatusResponse(BaseModel):
    id: int
    status: Literal['pending', 'paid', 'failed']


async def get_freekassa_payment(amount: int, order_id: int, pay: Literal['sbp', 'card']):
    url = 'https://api.fk.life/v1/orders/create'
    data = {
        'shopId': 32219,
        'nonce': int(datetime.datetime.today().timestamp()),
        'us_orderId': str(order_id),
        'i': 44 if pay == 'sbp' else 36,
        'email': f'{order_id}@telegram.org',
        'ip': '5.35.91.55',
        'success_url': config.bot.webhook_url + 'webapp/check_pay',
        'amount': str(amount),
        'currency': 'RUB'
    }
    data = _get_signature(data, config.freekassa.api_key)
    async with ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'url': data['location'],
    }


async def process_payment(order_id: int, oxa_id, cb_id: int, bot: Bot, session: DataInteraction, scheduler: AsyncIOScheduler, interval: int):
    try:
        await asyncio.wait_for(
            _check_payment(order_id, oxa_id, cb_id, bot, session, scheduler, interval),
            timeout=60 * 20)
    except TimeoutError:
        print(f"Платёж {order_id} истёк (таймаут)")

    except Exception as e:
        print(f"Ошибка в фоновом ожидании платежа {order_id}: {e}")


async def _check_payment(order_id: int, oxa_id, cb_id: int, bot: Bot, session: DataInteraction, scheduler: AsyncIOScheduler, interval: int):
    while True:
        status = await check_crypto_payment(cb_id)
        if status:
            order_storage[order_id]['status'] = 'paid'
            await execute_payment(order_id, bot, session, scheduler)
            break
        status = await check_oxa_payment(oxa_id)
        if status:
            order_storage[order_id]['status'] = 'paid'
            await execute_payment(order_id, bot, session, scheduler)
            break
        await asyncio.sleep(interval)
    return


async def execute_payment(order_id: int, bot: Bot, session: DataInteraction, scheduler: AsyncIOScheduler):
    order = order_storage.get(order_id)
    user_id = order.get('user_id')
    rate = order.get('rate')
    amount = order.get('amount')
    admin = await session.get_admin(user_id)
    await session.add_general_buys(rate, amount)
    await session.update_admin_sub(user_id, 1, rate)
    job_id = f'check_sub_{user_id}'
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
    scheduler.add_job(
        check_sub,
        'interval',
        args=[user_id, bot, session, scheduler],
        id=job_id,
        days=1
    )
    if not admin.sub:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='🎉<b>Поздравляю</b>, теперь вы официально партнер <b>TrustStars</b>\nЧтобы начать введите команду /start'
            )
        except Exception:
            ...
    else:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='🎉<b>Вы успешно продлили свою подписку\nЧтобы продолжить введите команду /start'
            )
        except Exception:
            ...


@webapp_router.get("/webapp/payment", response_model=PaymentResponse)  # Динамический путь для каждого бота
async def payment_handler(response: Request, rate: str, user_id: int):
    try:
        session: DataInteraction = response.app.state.session
        scheduler: AsyncIOScheduler = response.app.state.scheduler
        bot: Bot = response.app.state.bot
        usdt_rub = await _get_usdt_rub()
        usdt = rates[rate]
        amount = round(usdt * usdt_rub)
        order_id = random.randint(1, 99999)
        oxa_pay = await get_oxa_payment_data(amount)
        cb_pay = await get_crypto_payment_data(amount)
        card_pay = await get_freekassa_payment(amount, order_id, 'card')
        sbp_pay = await get_freekassa_payment(amount, order_id, 'sbp')
        task = asyncio.create_task(process_payment(order_id, oxa_pay.get('id'), cb_pay.get('id'), bot, session, scheduler, 5))
        order_storage[order_id] = {
            'user_id': user_id,
            'status': 'pending',
            'rate': rate,
            'amount': amount
        }
        card_pay = {
            'id': 'card',
            'url': card_pay.get('url'),
            'name': 'Карта',
            'icon': '💳'
        }
        sbp_pay = {
            'id': 'sbp',
            'url': sbp_pay.get('url'),
            'name': 'СБП',
            'icon': '💶'
        }
        oxa_pay = {
            'id': 'crypto',
            'url': oxa_pay.get('url'),
            'name': 'Крипта',
            'icon': '💵'
        }
        cb_pay = {
            'id': 'crypto_bot',
            'url': cb_pay.get('url'),
            'name': 'Криптобот',
            'icon': '💲'
        }
        return {
            'id': order_id,
            'amount': amount,
            'rate': rate,
            'payments': [
                card_pay,
                sbp_pay,
                oxa_pay,
                cb_pay
            ]
        }
    except Exception:
        return HTTPException(500, detail='Internal Server Error')


@webapp_router.get('/webapp/status', response_model=StatusResponse)
async def pay_status_handler(order_id: int):
    return {
        'id': order_id,
        'status': order_storage.get(order_id, {'status': 'failed'}).get('status')
    }


@webapp_router.post('/webapp/check_pay')
async def webapp_check_payment(response: Request, us_orderId: str = Form(...)):
    client_ip = response.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP {client_ip} is not allowed"
        )
    order_id = int(us_orderId)
    session: DataInteraction = response.app.state.session
    scheduler: AsyncIOScheduler = response.app.state.scheduler
    bot: Bot = response.app.state.bot
    order_storage[order_id]['status'] = 'paid'
    order = order_storage.get(order_id)
    user_id = order.get('user_id')
    rate = order.get('rate')
    amount = order.get('amount')
    admin = await session.get_admin(user_id)
    await session.add_general_buys(rate, amount)
    await session.update_admin_sub(user_id, 1, rate)
    job_id = f'check_sub_{user_id}'
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
    scheduler.add_job(
        check_sub,
        'interval',
        args=[user_id, bot, session, scheduler],
        id=job_id,
        days=1
    )
    if not admin.sub:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='🎉<b>Поздравляю</b>, теперь вы официально партнер <b>TrustStars</b>\nЧтобы начать введите команду /start'
            )
        except Exception:
            ...
    else:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='🎉<b>Вы успешно продлили свою подписку\nЧтобы продолжить введите команду /start'
            )
        except Exception:
            ...


