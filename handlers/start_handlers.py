from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram_dialog import DialogManager, StartMode

from database.action_data_class import DataInteraction
from states.state_groups import InitialSG, adminSG
from config_data.config import Config, load_config


config: Config = load_config()
start_router = Router()


@start_router.message(CommandStart())
async def start_dialog(msg: Message, dialog_manager: DialogManager, session: DataInteraction):
    await session.add_admin(msg.from_user.id, msg.from_user.username if msg.from_user.username else 'Отсутствует',
                            msg.from_user.full_name)
    await session.update_admin_sub(msg.from_user.id, 1)
    admin = await session.get_admin(msg.from_user.id)
    if dialog_manager.has_context():
        await dialog_manager.done()
        try:
            await msg.bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id - 1)
        except Exception:
            ...
    if not admin.sub:
        web_app = WebAppInfo(url=config.bot.webhook_url)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='⭐️Открыть франшизу!', web_app=web_app)]]
        )
        await msg.answer(
            text='<b>Добро пожаловать, партнер!</b> Жми кнопку ниже и '
                 'переходи в мини-приложение, чтобы начать зарабатывать вместе с нами!💰',
            reply_markup=keyboard)
        return
    if not admin.bot:
        await dialog_manager.start(InitialSG.start, mode=StartMode.RESET_STACK)
        return
    await dialog_manager.start(adminSG.start, mode=StartMode.RESET_STACK)
