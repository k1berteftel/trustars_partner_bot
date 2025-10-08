import os
import datetime

from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums.chat_action import ChatAction
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.build_ids import get_random_id
from utils.schedulers import send_messages
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, adminSG


config: Config = load_config()


async def menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    users = await session.get_users()
    admin = await session.get_admin(event_from_user.id)
    active = 0
    entry = {
        'today': 0,
        'yesterday': 0,
        '2_day_ago': 0
    }
    activity = 0
    for user in users:
        if user.active:
            active += 1
        for day in range(0, 3):
            #print(user.entry.date(), (datetime.datetime.today() - datetime.timedelta(days=day)).date())
            if user.entry.date() == (datetime.datetime.today() - datetime.timedelta(days=day)).date():
                if day == 0:
                    entry['today'] = entry.get('today') + 1
                elif day == 1:
                    entry['yesterday'] = entry.get('yesterday') + 1
                else:
                    entry['2_day_ago'] = entry.get('2_day_ago') + 1
        if user.activity.timestamp() > (datetime.datetime.today() - datetime.timedelta(days=1)).timestamp():
            activity += 1

    statistic = await session.get_bot_static()
    text = (f'<b>Статистика на {datetime.datetime.today().strftime("%d-%m-%Y")}</b>\n\nВсего пользователей: {len(users)}'
            f'\n - Активные пользователи(не заблокировали бота): {active}\n - Пользователей заблокировали '
            f'бота: {len(users) - active}\n - Провзаимодействовали с ботом за последние 24 часа: {activity}\n\n'
            f'<b>Прирост аудитории:</b>\n - За сегодня: +{entry.get("today")}\n - Вчера: +{entry.get("yesterday")}'
            f'\n - Позавчера: + {entry.get("2_day_ago")}\n\n<b>Общая выручка:</b> {statistic.earn}₽ \n'
            f' - Всего покупок: {statistic.payments}\n - Сумма покупок: {statistic.buys}₽ \n')  # <b>Вы заработали</b>:
    return {
        'text': text,
        'full': admin.rate == 'full'
    }


async def refresh_static(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await dialog_manager.switch_to(adminSG.start)


async def extend_message(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    web_app = WebAppInfo(url=config.bot.webhook_url + 'rates')
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='⭐️Продлить', web_app=web_app)]]
    )
    await clb.message.answer(
        text='<b>Добро пожаловать, партнер!</b> Жми кнопку ниже и '
             'переходи в мини-приложение, чтобы начать зарабатывать вместе с нами!💰',
        reply_markup=keyboard)


async def check_activity(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    msg = await clb.message.answer('🔄Начинаем проверку пользователей бота')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admin = await session.get_admin(clb.from_user.id)
    users = await session.get_users()
    bot = Bot(admin.bot.token)
    for user in users:
        try:
            await bot.send_chat_action(
                chat_id=user.user_id,
                action=ChatAction.TYPING
            )
            if not user.active:
                await session.set_active(user.user_id, 1)
        except Exception as err:
            if user.active:
                await session.set_active(user.user_id, 0)
    await msg.delete()
    await clb.message.answer('<b>Проверка активности завершена, проверьте пожалуйста статистику</b>')
    await dialog_manager.switch_to(adminSG.start)


async def get_users_txt(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    users = await session.get_users()
    with open('users.txt', 'a+') as file:
        for user in users:
            file.write(f'{user.user_id}\n')
    await clb.message.answer_document(
        document=FSInputFile(path='users.txt')
    )
    try:
        os.remove('users.txt')
    except Exception:
        ...


async def deeplink_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admin = await session.get_admin(event_from_user.id)
    bot = Bot(token=admin.bot.token)
    bot_data = await bot.get_me()
    links = await session.get_deeplinks()
    text = ''
    for link in links:
        text += f'https://t.me/{bot_data.username}?start={link.link}: {link.entry}\n'  # Получить ссылку на бота и поменять
    return {'links': text}


async def add_deeplink(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.add_deeplink(get_random_id())
    await dialog_manager.switch_to(adminSG.deeplink_menu)


async def del_deeplink(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.del_deeplink(item_id)
    await clb.answer('Ссылка была успешно удаленна')
    await dialog_manager.switch_to(adminSG.deeplink_menu)


async def del_deeplink_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    links = await session.get_deeplinks()
    buttons = []
    for link in links:
        buttons.append((f'{link.link}: {link.entry}', link.link))
    return {'items': buttons}


async def set_charge_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    static = await session.get_bot_static()
    return {
        'charge': static.charge
    }


async def get_charge(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        charge = int(text)
    except Exception:
        await msg.answer('❗️Введите пожалуйста число (от 0 до 100')
        return
    if not (10 <= charge < 100):
        await msg.answer('❗️Наценка должна быть не менее 10% и не более 100%')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.set_charge(charge)
    await dialog_manager.switch_to(adminSG.set_charge)


async def get_mail(msg: Message, widget: MessageInput, dialog_manager: DialogManager):
    if msg.text:
        dialog_manager.dialog_data['text'] = msg.text
    elif msg.photo:
        dialog_manager.dialog_data['photo'] = msg.photo[0].file_id
        dialog_manager.dialog_data['caption'] = msg.caption
    elif msg.video:
        dialog_manager.dialog_data['video'] = msg.video.file_id
        dialog_manager.dialog_data['caption'] = msg.caption
    else:
        await msg.answer('Что-то пошло не так, пожалуйста попробуйте снова')
    await dialog_manager.switch_to(adminSG.get_time)


async def get_time(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        time = datetime.datetime.strptime(text, '%H:%M %d.%m')
    except Exception as err:
        print(err)
        await msg.answer('Вы ввели данные не в том формате, пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['time'] = text
    await dialog_manager.switch_to(adminSG.get_keyboard)


async def get_mail_keyboard(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        buttons = text.strip().split('\n')
        keyboard: list[tuple] = [(i.split('-')[0].strip(), i.split('-')[1].strip()) for i in buttons]
    except Exception as err:
        print(err)
        await msg.answer('Вы ввели данные не в том формате, пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['keyboard'] = keyboard
    await dialog_manager.switch_to(adminSG.confirm_mail)


async def cancel_malling(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.start)


async def start_malling(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    time = dialog_manager.dialog_data.get('time')
    keyboard = dialog_manager.dialog_data.get('keyboard')
    if keyboard:
        keyboard = [InlineKeyboardButton(text=i[0], url=i[1]) for i in keyboard]
    users = await session.get_users()
    admin = await session.get_admin(clb.from_user.id)
    bot = Bot(token=admin.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    if not time:
        if dialog_manager.dialog_data.get('text'):
            text: str = dialog_manager.dialog_data.get('text')
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.user_id,
                        text=text.format(name=user.name),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)
        elif dialog_manager.dialog_data.get('caption'):
            caption: str = dialog_manager.dialog_data.get('caption')
            if dialog_manager.dialog_data.get('photo'):
                for user in users:
                    try:
                        await bot.send_photo(
                            chat_id=user.user_id,
                            photo=dialog_manager.dialog_data.get('photo'),
                            caption=caption.format(name=user.name),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
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
                            video=dialog_manager.dialog_data.get('video'),
                            caption=caption.format(name=user.name),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
                        )
                        if user.active == 0:
                            await session.set_active(user.user_id, 1)
                    except Exception as err:
                        print(err)
                        await session.set_active(user.user_id, 0)
    else:
        date = datetime.datetime.strptime(time, '%H:%M %d.%m')
        date = date.replace(year=datetime.datetime.now().year)
        scheduler.add_job(
            func=send_messages,
            args=[bot, session, InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None],
            kwargs={
                'text': dialog_manager.dialog_data.get('text'),
                'caption': dialog_manager.dialog_data.get('caption'),
                'photo': dialog_manager.dialog_data.get('photo'),
                'video': dialog_manager.dialog_data.get('video')
            },
            next_run_time=date
        )
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.start)


async def get_derive_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Сумма для вывода должна быть числом, пожалуйста попробуйте снова')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    static = await session.get_bot_static()
    if amount > static.earn:
        await msg.answer('❗️Сумма для вывода должна быть не больше той что сейчас у вас')
        return
    username = msg.from_user.username
    if not username:
        await msg.answer(text='❗️Чтобы получить выплату, пожалуйста поставьте на свой аккаунт юзернейм')
        return
    text = (f'<b>Заявка на вывод средств</b>\n\nДанные о пользователе:\n'
            f'- Никнейм: {msg.from_user.name}\n - Username: @{msg.from_user.username}'
            f'\n - Telegram Id: {msg.from_user.id}\n'
            f'\n - Общий баланс: {static.earn}️₽ \n - <b>Сумма для вывода</b>: {amount}️₽ ')
    for admin in config.bot.admin_ids:
        try:
            await msg.bot.send_message(
                chat_id=admin,
                text=text
            )
        except Exception:
            ...
    await session.clear_earn()
    await msg.answer('✅Заявка на вывод средств была успешно отправлена')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.start)

