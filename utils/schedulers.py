import asyncio
from aiogram import Bot
from aiogram_dialog import DialogManager
from aiogram.types import InlineKeyboardMarkup, Message
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.action_data_class import DataInteraction


async def send_messages(bot: Bot, session: DataInteraction, keyboard: InlineKeyboardMarkup | None, message: Message, **kwargs):
    users = await session.get_users()
    text = kwargs.get('text')
    caption = kwargs.get('caption')
    photo = kwargs.get('photo')
    video = kwargs.get('video')
    if text:
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.user_id,
                    text=text.format(name=user.name),
                    reply_markup=keyboard
                )
                if user.active == 0:
                    await session.set_active(user.user_id, 1)
            except Exception as err:
                print(err)
                await session.set_active(user.user_id, 0)
    elif caption:
        if photo:
            for user in users:
                try:
                    await bot.send_photo(
                        chat_id=user.user_id,
                        photo=photo,
                        caption=caption.format(name=user.name),
                        reply_markup=keyboard
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)
        else:
            for user in users:
                try:
                    await bot.send_video(
                        chat_id=user.user_id,
                        video=video,
                        caption=caption.format(name=user.name),
                        reply_markup=keyboard
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)


async def clean_applications(session: DataInteraction):
    today = (datetime.today() - timedelta(days=14)).timestamp()
    for application in await session.get_applications():
        if application.create.timestamp() <= today:
            await session.del_application(application.uid_key)


async def check_sub(user_id: int, bot: Bot, session: DataInteraction, scheduler: AsyncIOScheduler):
    user = await session.get_admin(user_id)
    dif = (user.sub - datetime.now()).days
    text = ''
    if dif == 5:
        text = f'До окончания периода подписки осталось 5 дней'
    if dif == 1:
        text = f'До окончания периода подписки остался 1 день'
    if dif <= 0:
        text = 'К сожалению срок действия подписки подошел к концу'
        await session.update_admin_sub(user_id, None)

        token = user.bot.token
        session: DataInteraction = DataInteraction(session._sessions, user.bot.token)
        await session.set_bot_active(False)
        admin_bot = Bot(token=token)
        await admin_bot.delete_webhook()

        job_id = f'check_sub_{user_id}'
        job = scheduler.get_job(job_id=job_id)
        if job:
            job.remove()
    if text:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text
            )
        except Exception:
            await session.set_active(user_id, 0)