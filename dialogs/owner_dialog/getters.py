import datetime
import os
from typing import Literal

from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums.chat_action import ChatAction
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.tables import get_table
from utils.schedulers import check_sub
from database.model import BotsTable
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import OwnerSG


async def get_static(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = await session.get_admins()
    entry = {
        'today': 0,
        'yesterday': 0,
        '2_day_ago': 0
    }
    subs = 0
    for user in admins:
        if user.sub:
            subs += 1
        for day in range(0, 3):
            #print(user.entry.date(), (datetime.datetime.today() - datetime.timedelta(days=day)).date())
            if user.entry.date() == (datetime.datetime.today() - datetime.timedelta(days=day)).date():
                if day == 0:
                    entry['today'] = entry.get('today') + 1
                elif day == 1:
                    entry['yesterday'] = entry.get('yesterday') + 1
                else:
                    entry['2_day_ago'] = entry.get('2_day_ago') + 1
    static = await session.get_general_static()
    text = (f'<b>Статистика на {datetime.datetime.today().strftime("%d-%m-%Y")}</b>\n\nВсего партнеров: {len(admins)}\n'
            f'Из них приобрели тариф: {subs}\n\n'
            f'<b>Прирост партнеров:</b>\n - За сегодня: +{entry.get("today")}\n - Вчера: +{entry.get("yesterday")}'
            f'\n - Позавчера: + {entry.get("2_day_ago")}\n\n<b>Общие показатели продаж:</b>\n'
            f'- Всего покупок (в ботах) - {static.buys}\n - Продано на сумму: {static.sum}₽\n<b>По тарифам:</b>\n'
            f' -Покупок <em>STANDART</em>: {static.standard_buys} ({static.standard}$)\n - Покупок <em>FULL</em>: '
            f'{static.full_buys} ({static.full}$)\n\n<b>Всего заработано: {static.earn}₽</b>')
    await clb.message.answer(text)


async def upload_partners(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = await session.get_admins()
    columns = []
    for admin in admins:
        if admin.sub:
            bot_db: BotsTable = admin.bot
            bot = Bot(bot_db.token)
            bot_data = await bot.get_me()
            static = await session.get_bot_static(bot_db.token)
            columns.append(
                [
                    admin.name,
                    '@' + admin.username if admin.username else '-',
                    admin.rate,
                    admin.sub.strftime("%d-%m-%Y"),
                    static.earn,
                    bot_data.username
                ]
            )
    columns.insert(0, ['Никнейм', 'Юзернейм', 'Тариф', 'Подписка до', 'Заработал', 'Бот'])
    table = get_table(columns, 'Активные партнеры')
    await clb.message.answer_document(
        document=FSInputFile(path=table)
    )
    try:
        os.remove(table)
    except Exception:
        ...


async def get_admin_data(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    try:
        user_id = int(text)
        user = await session.get_admin(user_id)
    except Exception:
        if not text.startswith('@'):
            await msg.answer('Юзернейм должен начинаться с @ , пожалуйста попробуйте снова')
            return
        user = await session.get_admin_by_username(text[1::])
    if not user:
        await msg.answer('Такого пользователя в боте не найдено, пожалуйста попробуйте еще раз')
        return
    dialog_manager.dialog_data['user_id'] = user.user_id
    await dialog_manager.switch_to(OwnerSG.rate_choose)


async def rate_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    rate = clb.data.split('_')[0]
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    user_id = dialog_manager.dialog_data.get('user_id')
    await session.update_admin_sub(user_id, 1, rate)
    job_id = f'check_sub_{user_id}'
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
    scheduler.add_job(
        check_sub,
        'interval',
        args=[user_id, clb.bot, session, scheduler],
        id=job_id,
        days=1
    )
    await clb.answer('Подписка была успешно выдана')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(OwnerSG.start)


async def get_app_uid(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        uid_key = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('Номер заказа должен быть числом, пожалуйста попробуйте еще раз')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    application = await session.get_application(uid_key)
    if not application:
        await msg.answer('Заказа с таким номером не найдено')
        return
    dialog_manager.dialog_data['uid_key'] = application.uid_key
    await dialog_manager.switch_to(OwnerSG.application_menu)


async def application_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    uid_key = dialog_manager.dialog_data.get('uid_key')
    application = await session.get_application(uid_key)
    user = await session.get_user(application.user_id)
    statuses = {
        0: 'Не оплачен',
        1: 'В процессе выполнения',
        2: 'Оплачен',
        3: 'Ошибка выполнения'
    }
    payments = {
        None: 'Не оплачен',
        'sbp': 'СБП',
        'card': 'Карта',
        'crypto': 'Крипта (Oxa pay)',
        'crypto_bot': 'Криптобот'
    }
    types = {
        'stars': 'Покупка звезд',
        None: 'Покупка звезд',
        'premium': 'Покупка премиум',
        'ton': 'Покупка TON'
    }
    text = (f'<b>Тип заказа</b>: {types.get(application.type)}\n'
            f'<b>Номер заказа</b>: {application.uid_key}\n<b>Создал</b>: {application.user_id} (@{user.username})'
            f'\n<b>Получатель</b>: @{application.receiver}\n<b>Сумма</b>: {application.amount} звезд\n'
            f'<b>Стоимость</b>: {float(application.rub)}₽ ({application.usdt}$)\n<b>Статус заказа</b>: {statuses[application.status]}'
            f'\n<b>Статус оплаты</b>: {payments[application.payment]}'
            f'\n<b>Дата создания</b>: {application.create.strftime("%Y-%m-%d %H:%M:%S")}')
    return {'text': text}
