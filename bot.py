import asyncio
import logging
import os
import inspect
import pytz
import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiogram import Bot, Dispatcher
from aiogram_dialog import setup_dialogs
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend import router, webapp_router
from services.start_consumer import start_transfer_consumer
from storage.nats_storage import NatsStorage
from utils.nats_connect import connect_to_nats
from utils.schedulers import clean_applications

from database.action_data_class import setup_database, DataInteraction
from database.build import PostgresBuild
from database.model import Base

from config_data.config import load_config, Config
from configurate.dispatcher import configurate_dp, configurate_bot_dp


timezone = pytz.timezone('Europe/Moscow')
datetime.datetime.now(timezone)

module_path = inspect.getfile(inspect.currentframe())
module_dir = os.path.realpath(os.path.dirname(module_path))


format = '[{asctime}] #{levelname:8} {filename}:' \
         '{lineno} - {name} - {message}'

logging.basicConfig(
    level=logging.DEBUG,
    format=format,
    style='{'
)


logger = logging.getLogger(__name__)

config: Config = load_config()

allowed_updates = [
    "message", "edited_message", "channel_post", "edited_channel_post",
    "inline_query", "chosen_inline_result", "callback_query",
    "shipping_query", "pre_checkout_query", "poll", "poll_answer",
    "my_chat_member", "chat_member", "chat_join_request"
]

database = PostgresBuild(config.db.dns)
bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
bot_dp = Dispatcher()


async def setup_bots(db: DataInteraction):
    bots = await db.get_bots()
    for db_bot in bots:
        if not db_bot.active:
            bot = Bot(token=db_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            webhook_url = f"{config.bot.webhook_url}webhook/{db_bot.id}"
            await bot.delete_webhook(drop_pending_updates=True)
            await bot.set_webhook(url=webhook_url, allowed_updates=allowed_updates)


async def main():
    #await database.drop_tables(Base)
    await database.create_tables(Base)
    session = database.session()
    await setup_database(session)
    db = DataInteraction(session, None)

    scheduler: AsyncIOScheduler = AsyncIOScheduler()
    scheduler.start()

    scheduler.add_job(
        clean_applications,
        'interval',
        args=[db],
        hours=4
    )

    nc, js = await connect_to_nats(servers=config.nats.servers)

    await bot.delete_webhook(drop_pending_updates=True)
    await configurate_dp(dp)
    await configurate_bot_dp(bot_dp)

    await setup_bots(db)

    app = FastAPI()
    app.include_router(router)
    app.include_router(webapp_router)
    app.state.nc = nc
    app.state.js = js
    app.state.scheduler = scheduler
    app.state.session = db
    app.state.dp = bot_dp
    app.state.bot = bot

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn_config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level="info")  # ssl_keyfile='ssl/key.pem', ssl_certfile='ssl/cert.pem'
    server = uvicorn.Server(uvicorn_config)

    aiogram_task = asyncio.create_task(dp.start_polling(bot, _session=session, _scheduler=scheduler, js=js))
    uvicorn_task = asyncio.create_task(server.serve())
    consumer_task = asyncio.create_task(start_transfer_consumer(
        nc=nc,
        js=js,
        sessions=session,
        scheduler=scheduler,
        subject=config.consumer.subject,
        stream=config.consumer.stream,
        durable_name=config.consumer.durable_name
    ))

    try:
        await asyncio.gather(aiogram_task, uvicorn_task, consumer_task)
    except Exception as e:
        logger.exception(e)
    finally:
        await nc.close()
        logger.info('Connection closed')


if __name__ == "__main__":
    asyncio.run(main())