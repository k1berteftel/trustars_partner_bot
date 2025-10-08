from aiogram import Dispatcher
from aiogram_dialog import setup_dialogs

from handlers import start_router, user_router
from dialogs import admin_dialog, start_dialog, user_dialog, payment_dialog, owner_dialog
from middlewares import TransferObjectsMiddleware, RemindMiddleware


async def configurate_dp(dp: Dispatcher):
    # подключаем роутеры
    dp.include_routers(start_router, start_dialog, admin_dialog, owner_dialog)

    # подключаем middleware
    dp.update.middleware(TransferObjectsMiddleware(True))
    dp.update.middleware(RemindMiddleware())

    setup_dialogs(dp)


async def configurate_bot_dp(dp: Dispatcher):
    dp.include_routers(user_router, user_dialog, payment_dialog)

    dp.update.middleware(TransferObjectsMiddleware(False))
    dp.update.middleware(RemindMiddleware())

    setup_dialogs(dp)