import os
import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, User, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_dialog import DialogManager, StartMode
from aiogram.utils.token import validate_token, TokenValidationError
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.build_ids import get_random_id
from utils.schedulers import send_messages
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import adminSG


allowed_updates = [
    "message", "edited_message", "channel_post", "edited_channel_post",
    "inline_query", "chosen_inline_result", "callback_query",
    "shipping_query", "pre_checkout_query", "poll", "poll_answer",
    "my_chat_member", "chat_member", "chat_join_request"
]

config: Config = load_config()


async def get_token(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    if not validate_token(text):
        await msg.answer('❗️Токен невалиден, пожалуйста попробуйте еще раз')
        return
    status = await session.add_bot(msg.from_user.id, text)
    if not status:
        await msg.answer('❗️К сожалению данный бот уже добавлен, пожалуйста попробуйте другой токен')
        return
    bot = Bot(token=text, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    db_bot = await session.get_bot_by_token(text)
    webhook_url = f"{config.bot.webhook_url}webhook/{db_bot.id}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url, allowed_updates=allowed_updates)
    await dialog_manager.done()
    await msg.delete()
    await msg.answer('✅<b>Бот успешно добавлен</b>, для перезапуска введите команду /start')
    # TODO: если возможно автомат перевод в главное меню или на крайняк кнопка открытия
    """
    if dialog_manager.has_context():
        await dialog_manager.done()
        try:
            await msg.bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id - 1)
        except Exception:
            ...
    await dialog_manager.start(adminSG.start, mode=StartMode.RESET_STACK)
    """
