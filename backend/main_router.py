
from aiogram import types, Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Request, Form, HTTPException, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config


config: Config = load_config()


ALLOWED_IPS: list[str] = [
    "168.119.157.136",
    "168.119.60.227",
    "178.154.197.79",
    "51.250.54.238"
]


router = APIRouter()


@router.post("/webhook/{bot_id}")  # Динамический путь для каждого бота
async def common_webhook_handler(bot_id: str, request: Request):

    update = await request.json()
    telegram_update = types.Update.model_validate(update)

    session: DataInteraction = request.app.state.session
    dp: Dispatcher = request.app.state.dp
    scheduler: AsyncIOScheduler = request.app.state.scheduler

    db_bot = await session.get_bot_by_id(int(bot_id))
    bot = Bot(token=db_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    try:
        await dp.feed_update(bot=bot, update=telegram_update, _session=session._sessions, _scheduler=scheduler)
    except Exception as err:
        print(err)
        await bot.session.close()
        return {'ok': False}
    await bot.session.close()
    return {"ok": True}


@router.post("/payment")
async def ping(response: Request, us_userId: str = Form(...), us_appId: str = Form(...),
               us_botId: str = Form(...), CUR_ID: str | int = Form(...)):
    client_ip = response.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP {client_ip} is not allowed"
        )
    user_id = int(us_userId)
    app_id = int(us_appId)
    bot_id = int(us_botId)
    session: DataInteraction = response.app.state.session
    scheduler: AsyncIOScheduler = response.app.state.scheduler
    js: JetStreamContext = response.app.state.js
    application = await session.get_application(app_id)
    if application.status in [0, 2, 3]:
        return "OK"
    trans_type = int(CUR_ID)
    payment = ''
    if trans_type == 36:
        payment = 'card'
    if trans_type == 44:
        payment = 'sbp'
    data = {
        'transfer_type': application.type,
        'username': application.receiver,
        'currency': application.amount,
        'payment': payment,
        'app_id': application.uid_key,
        'bot_id': bot_id
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )
    job = scheduler.get_job(f'payment_{user_id}')
    if job:
        job.remove()
    stop_job = scheduler.get_job(f'stop_payment_{user_id}')
    if stop_job:
        stop_job.remove()
    return "OK"
