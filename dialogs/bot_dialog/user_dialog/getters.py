import os

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import CallbackQuery, User, Message, ContentType, FSInputFile
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nats.js import JetStreamContext

from utils.payments.create_payment import (get_crypto_payment_data, get_oxa_payment_data, get_freekassa_sbp,
                                           get_freekassa_card, _get_ton_usdt, _get_usdt_rub)
from utils.transactions import check_user_premium, get_stars_price
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, PaymentSG

config: Config = load_config()

premium_usdt = {
    3: 12,
    6: 16,
    12: 29
}


async def rules_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    text = (
        '<b>Политика использования</b>\nЦель магазина: Магазин предоставляет услуги по продаже звезд в Telegram.\n\n'
        'Правила использования: Пользователи обязаны соблюдать все применимые законы и правила платформ,'
        ' на которых они используют купленные звезды. Запрещены попытки обмана, мошенничество и другие '
        'недопустимые действия.\n\nПрием платежей: Мы принимаем платежи через указанные методы, '
        'обеспечивая безопасность и конфиденциальность ваших данных.\n\nОбязательства магазина:'
        ' Магазин обязуется предоставить вам купленные звезды после успешной оплаты.\n\nОтветственность '
        'пользователя: Вы несете ответственность за предоставление правильной информации при заказе услуги.'
        ' Пользователи должны предоставить корректные данные для успешного выполнения заказа.\n\nЗапрещенные'
        ' действия: Запрещены действия, направленные на мошенничество, включая попытки '
        'возврата средств после получения услуги.\n\n<b>Политика возврата</b>\nУсловия возврата: Вы можете '
        'запросить возврат средств, если не получили звезд. Нужны скрины оплаты и главной страницы бота.\n\n'
        'Процедура возврата: Для запроса возврата, свяжитесь с нашей службой поддержки по указанным '
        'контактным данным. Мы рассмотрим ваш запрос и произведем возврат средств на вашу карту/кошелек.\n\n'
        'Сроки возврата: Вы получите средства в течение 3 рабочих дней.\n\n<b>Политика конфиденциальности</b>\n'
        'Сбор информации: Мы можем собирать определенную информацию от пользователей для обработки заказов '
        'и улучшения сервиса.\n\nИспользование информации: Мы обеспечиваем безопасное и конфиденциальное '
        'хранение ваших данных. Информация будет использована исключительно для обработки заказов и '
        'обратной связи с вами.\n\nРазглашение информации: Мы не раскроем вашу информацию третьим '
        'лицам, за исключением случаев, предусмотренных законом или в случаях, когда это необходимо '
        'для выполнения заказа (например, передача информации платежным системам).\n\nСогласие пользователя: '
        'Используя наши услуги, вы соглашаетесь с нашей политикой конфиденциальности.')
    return {'text': text}


async def buy_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    buy = clb.data.split('_')[0]
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['buy'] = buy
    if buy == 'ton':
        await dialog_manager.switch_to(startSG.ton_receipt_menu)
        return
    await dialog_manager.switch_to(startSG.get_username)


async def get_username_getter(dialog_manager: DialogManager, **kwargs):
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'ton':
        text = 'TON'
    elif buy == 'premium':
        text = 'Премиум'
    else:
        text = 'Звезды'
    return {'present': text}


async def get_stars_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    # await msg.answer('На данный момент в боте ведутся <b>технические работы</b>, приносим свои извинения🙏   ')
    # await dialog_manager.switch_to(startSG.start)
    # return
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во звезд должно быть числом, пожалуйста попробуйте снова')
        return
    if not (50 <= amount <= 100000):
        await msg.answer('❗️Кол-во звезд должно быть больше 50 и меньше 1000000')
        return
    dialog_manager.dialog_data['amount'] = amount
    start_data = {
        'currency': dialog_manager.dialog_data.get('amount'),
        'rate': dialog_manager.dialog_data.get('buy'),
        'username': dialog_manager.dialog_data.get('username')
    }
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def premium_rate_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    months = int(clb.data.split('_')[0])
    dialog_manager.dialog_data['months'] = months
    start_data = {
        'currency': months,
        'rate': dialog_manager.dialog_data.get('buy'),
        'username': dialog_manager.dialog_data.get('username')
    }
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def get_ton_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во TON должно быть числом, пожалуйста попробуйте снова')
        return
    if not (1 <= amount < 100):
        await msg.answer('❗️Кол-во TON должно быть больше 1 и меньше 100')
        return
    dialog_manager.dialog_data['amount'] = amount
    start_data = {
        'currency': dialog_manager.dialog_data.get('amount'),
        'rate': dialog_manager.dialog_data.get('buy'),
        'username': dialog_manager.dialog_data.get('username')
    }
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def get_rate_amount_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    username = dialog_manager.dialog_data.get('username')
    address = dialog_manager.dialog_data.get('address')
    buy = dialog_manager.dialog_data.get('buy')
    if buy in ['stars', 'premium']:
        return {
            'username': username,
            'address': False
        }
    else:
        if address:
            return {
                'username': False,
                'address': address
            }
        else:
            return {
                'username': username,
                'address': False
            }


async def get_username(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    if not text.startswith('@'):
        await msg.answer('❗️Юзернейм должен начинаться со знака @')
        return
    # проверка пользователя на существование
    dialog_manager.dialog_data['username'] = text
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'stars':
        await dialog_manager.switch_to(startSG.get_stars_amount)
    elif buy == 'premium':
        status = await check_user_premium(text, 12)
        if not status:
            await msg.answer('❗️У данного пользователя уже есть Премиум, пожалуйста попробуйте кого-нибудь еще')
            return
        await dialog_manager.switch_to(startSG.get_premium_rate)
    else:
        await dialog_manager.switch_to(startSG.get_ton_amount)


async def skip_get_username(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    username = clb.from_user.username
    if not username:
        await clb.message.answer('❗️Чтобы совершать покупки, пожалуйста поставьте на свой аккаунт юзернейм')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.username != username:
        await session.update_username(clb.from_user.id, username)
    dialog_manager.dialog_data['username'] = username
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'stars':
        await dialog_manager.switch_to(startSG.get_stars_amount)
    elif buy == 'premium':
        status = await check_user_premium(username, 12)
        if not status:
            await clb.message.answer('❗️У вас уже есть Премиум, пожалуйста попробуйте кого-нибудь еще')
            return
        await dialog_manager.switch_to(startSG.get_premium_rate)
    else:
        await dialog_manager.switch_to(startSG.get_ton_amount)




