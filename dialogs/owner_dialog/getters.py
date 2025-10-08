import datetime

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
            f' -Покупок <em>STANDART</em>: {static.standard_buys} ({static.standard}₽)\n - Покупок <em>FULL</em>: '
            f'{static.full_buys} ({static.full}₽)\n\n<b>Всего заработано: {static.earn}₽</b>')
    await clb.message.answer(text)