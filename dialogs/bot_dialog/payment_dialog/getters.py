import asyncio

from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from nats.js import JetStreamContext

from utils.payments.create_payment import (get_oxa_payment_data, get_crypto_payment_data,
                                           get_freekassa_sbp, get_freekassa_card, _get_usdt_rub)
from utils.payments.process_payment import wait_for_payment
from utils.transactions import get_stars_price
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, PaymentSG


premium_usdt = {
    3: 12,
    6: 16,
    12: 29
}


async def menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    if dialog_manager.start_data:
        dialog_manager.dialog_data['rate'] = dialog_manager.start_data.get('rate')
        dialog_manager.dialog_data['username'] = dialog_manager.start_data.get('username')
        dialog_manager.dialog_data['currency'] = dialog_manager.start_data.get('currency')
        dialog_manager.start_data.clear()
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    currency = dialog_manager.dialog_data.get('currency')
    static = await session.get_bot_static()
    usdt_rub = await _get_usdt_rub()
    if rate == 'stars':
        usdt = await get_stars_price(currency)
        amount = round((usdt * usdt_rub) / (1 - static.charge / 100), 2)
        usdt = round(amount / usdt_rub, 2)
        text = (f'<blockquote> - <b>Номер заказа:</b> <code>{{app_id}}</code>\n - Получатель: {username}\n'
                f' - Количество звезд: {currency}\n - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>')
    else:
        usdt = premium_usdt[currency]
        amount = round((usdt * usdt_rub) / (1 - static.charge / 100), 2)
        usdt = round(amount / (usdt_rub), 2)
        text = (f'<blockquote> - <b>Номер заказа:</b> <code>{{app_id}}</code>\n - Получатель: {username}\n'
                f' - Подписка на: {currency} (месяцы)\n - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>')
    app_id = dialog_manager.dialog_data.get('app_id')
    if not app_id:
        user = await session.get_user(event_from_user.id)
        application = await session.add_application(user.id, username, currency, amount, usdt, rate)
        app_id = application.uid_key
        dialog_manager.dialog_data['app_id'] = app_id
    text = text.format(app_id=app_id)
    return {'text': text}


async def payment_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    js: JetStreamContext = dialog_manager.middleware_data.get('js')
    bot: Bot = dialog_manager.middleware_data.get('bot')
    db_bot = await session.get_bot_by_token(bot.token)
    payment_type = clb.data.split('_')[0]
    app_id = dialog_manager.dialog_data.get('app_id')
    rate = dialog_manager.dialog_data.get('rate')
    currency = dialog_manager.dialog_data.get('currency')
    username = dialog_manager.dialog_data.get('username')
    promo = dialog_manager.dialog_data.get('promo')
    static = await session.get_bot_static()
    usdt_rub = await _get_usdt_rub()
    if rate == 'stars':
        usdt = await get_stars_price(currency)
        amount = round((usdt * usdt_rub) / (1 - static.charge / 100), 2)
        if promo:
            amount = amount - (amount * promo / 100)
        usdt = round(amount / usdt_rub, 2)
    else:
        usdt = premium_usdt[currency]
        amount = round((usdt * usdt_rub) / (1 - static.charge / 100), 2)
        usdt = round(amount / (usdt_rub), 2)

    if payment_type == 'card':
        payment = await get_freekassa_card(clb.from_user.id, amount, app_id, db_bot.id)
    elif payment_type == 'sbp':
        payment = await get_freekassa_sbp(clb.from_user.id, amount, app_id, db_bot.id)
    elif payment_type == 'crypto':
        payment = await get_oxa_payment_data(amount)
        task = asyncio.create_task(
            wait_for_payment(
                payment_id=payment.get('id'),
                user_id=clb.from_user.id,
                app_id=app_id,
                bot=bot,
                session=session,
                js=js,
                currency=currency,
                rate=rate,
                payment_type='crypto',
            )
        )
        for active_task in asyncio.all_tasks():
            if active_task.get_name() == f'process_payment_{clb.from_user.id}':
                active_task.cancel()
        task.set_name(f'process_payment_{clb.from_user.id}')
    else:
        payment = await get_crypto_payment_data(amount)
        task = asyncio.create_task(
            wait_for_payment(
                payment_id=payment.get('id'),
                user_id=clb.from_user.id,
                app_id=app_id,
                bot=bot,
                session=session,
                js=js,
                currency=currency,
                rate=rate,
                payment_type='cryptoBot',
            )
        )
        for active_task in asyncio.all_tasks():
            if active_task.get_name() == f'process_payment_{clb.from_user.id}':
                active_task.cancel()
        task.set_name(f'process_payment_{clb.from_user.id}')
    dialog_manager.dialog_data['url'] = payment.get('url')
    dialog_manager.dialog_data['amount'] = amount
    dialog_manager.dialog_data['usdt'] = usdt
    await dialog_manager.switch_to(PaymentSG.process_payment)


async def process_payment_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    amount = dialog_manager.dialog_data.get('amount')
    usdt = dialog_manager.dialog_data.get('usdt')
    url = dialog_manager.dialog_data.get('url')
    app_id = dialog_manager.dialog_data.get('app_id')
    text = f'<blockquote> - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>\n<b> - Номер заказа: {app_id}</b>'
    return {
        'text': text,
        'url': url
    }


async def close_payment(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    name = f'process_payment_{clb.from_user.id}'
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            task.cancel()
    await dialog_manager.switch_to(PaymentSG.menu)
