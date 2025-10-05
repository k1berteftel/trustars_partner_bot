import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.action_data_class import DataInteraction

logger = logging.getLogger(__name__)


class TransferObjectsMiddleware(BaseMiddleware):

    def __init__(self, admin: bool = False):
        self._admin = admin

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:

        user: User = data.get('event_from_user')
        bot: Bot = data.get('bot')

        if user is None:
            return await handler(event, data)

        sessions: async_sessionmaker = data.get('_session')
        scheduler: AsyncIOScheduler = data.get('_scheduler')

        if self._admin:
            admin = await DataInteraction(sessions, None).get_admin(user.id)
            if admin:
                interaction = DataInteraction(sessions, admin.bot.token if admin.bot else None)
            else:
                interaction = DataInteraction(sessions, None)
        else:
            interaction = DataInteraction(sessions, bot.token)
        data['session'] = interaction
        data['scheduler'] = scheduler
        return await handler(event, data)