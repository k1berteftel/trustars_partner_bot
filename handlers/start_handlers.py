from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram_dialog import DialogManager, StartMode

from database.action_data_class import DataInteraction
from states.state_groups import InitialSG, adminSG, OwnerSG
from config_data.config import Config, load_config


config: Config = load_config()
start_router = Router()


@start_router.message(CommandStart())
async def start_dialog(msg: Message, dialog_manager: DialogManager, session: DataInteraction):
    await session.add_admin(msg.from_user.id, msg.from_user.username if msg.from_user.username else 'Отсутствует',
                            msg.from_user.full_name)
    #await session.update_admin_sub(msg.from_user.id, 1, 'full')
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


@start_router.message(Command('help'))
async def send_policy(msg: Message, dialog_manager: DialogManager):
    text = ('<b>Политика использования</b>\n\nЦель магазина: Магазин зани Ма носы продажей франшизы бота '
            '@TrustStarsbot\n\nПравила использования: Пользователи обязаны соблюдать все применимые '
            'законы и правила платформ, на которых они используют купленные звезды. Запрещены попытки обмана, '
            'мошенничество и другие недопустимые действия.\n\nПрием платежей: Мы принимаем платежи через указанные '
            'методы, обеспечивая безопасность и конфиденциальность ваших данных.\n\nОбязательства магазина: '
            'Магазин обязуется предоставить вам купленный товар после успешной оплаты.\n\nОтветственность '
            'пользователя: Вы несете ответственность за предоставление правильной информации при заказе услуги. '
            'Пользователи должны предоставить корректные данные для успешного выполнения заказа.\n\nЗапрещенные '
            'действия: Запрещены действия, направленные на мошенничество, включая попытки возврата средств после '
            'получения услуги.\n\n<b>Политика возврата</b>\nУсловия возврата: Вы можете запросить возврат средств, '
            'если не получили товар. Нужны скрины оплаты и главной страницы бота.\n\n\nПроцедура возврата: '
            'Для запроса возврата, свяжитесь с нашей службой поддержки по указанным контактным данным. '
            'Мы рассмотрим ваш запрос и произведем возврат средств на вашу карту/кошелек.\n\nСроки возврата: '
            'Вы получите средства в течение 3 рабочих дней.\n\n<b>Политика конфиденциальности</b>\nСбор информации: '
            'Мы можем собирать определенную информацию от пользователей для обработки заказов и улучшения '
            'сервиса.\n\nИспользование информации: Мы обеспечиваем безопасное и конфиденциальное хранение ваших данных.'
            ' Информация будет использована исключительно для обработки заказов и обратной связи с вами.\n\nРазглашение'
            ' информации: Мы не раскроем вашу информацию третьим лицам, за исключением случаев, предусмотренных '
            'законом или в случаях, когда это необходимо для выполнения заказа (например, передача информации '
            'платежным системам).\n\nСогласие пользователя: Используя наши услуги, вы соглашаетесь с нашей политикой '
            'конфиденциальности.')
    await msg.answer(text)


@start_router.message(Command('admin'))
async def start_owner_dialog(msg: Message, dialog_manager: DialogManager):
    if msg.from_user.id not in config.bot.admin_ids:
        return
    await dialog_manager.start(OwnerSG.start, mode=StartMode.RESET_STACK)

