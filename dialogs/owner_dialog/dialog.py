from aiogram.types import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url, Cancel
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.owner_dialog import getters
from states.state_groups import OwnerSG


owner_dialog = Dialog(
    Window(
        Const('Админ панель'),
        Column(
            Button(Const('📊 Получить статистику'), id='get_static', on_click=getters.get_static),
            SwitchTo(Const('Найти заказ'), id='get_app_uid_switcher', state=OwnerSG.get_app_uid),
            Button(Const('Выгрузка данных о партнерах'), id='partners_upload', on_click=getters.upload_partners),
            SwitchTo(Const('Выдать подписку'), id='get_admin_data_switcher', state=OwnerSG.get_admin_data),
            SwitchTo(Const('Добавить покупку партнеру'), id='get_partner_token', state=OwnerSG.get_partner_token),
        ),
        Cancel(Const('Закрыть админку'), id='close_admin'),
        state=OwnerSG.start
    ),
    Window(
        Const('Отправьте токен бота которому вы хотели бы добавить в статистику покупку'),
        TextInput(
            id='get_partner_token',
            on_success=getters.get_partner_token
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=OwnerSG.start),
        state=OwnerSG.get_partner_token
    ),
    Window(
        Const('Введите сумму покупки в рублях'),
        TextInput(
            id='get_earn_amount',
            on_success=getters.get_earn_amount
        ),
        SwitchTo(Const('🔙Назад'), id='back_get_partner_token', state=OwnerSG.get_partner_token),
        state=OwnerSG.get_earn_amount
    ),
    Window(
        Const('Введите Telegram ID или @username партнера, которому вы хотели бы выдать подписку'),
        TextInput(
            id='get_admin_data',
            on_success=getters.get_admin_data
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=OwnerSG.start),
        state=OwnerSG.get_admin_data
    ),
    Window(
        Const('Выберите тариф, который вы хотели бы выдать данному пользователю'),
        Column(
            Button(Const('Standart'), id='standart_rate_choose', on_click=getters.rate_choose),
            Button(Const('FULL'), id='full_rate_choose', on_click=getters.rate_choose)
        ),
        SwitchTo(Const('🔙Назад'), id='back_get_admin_data', state=OwnerSG.get_admin_data),
        state=OwnerSG.rate_choose
    ),
    Window(
        Const('Введите номер заказа'),
        TextInput(
            id='get_app_uid',
            on_success=getters.get_app_uid
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=OwnerSG.start),
        state=OwnerSG.get_app_uid
    ),
    Window(
        Format('<b>Данные по заказу</b>\n\n{text}'),
        SwitchTo(Const('🔙 Назад'), id='back_get_app_uid', state=OwnerSG.get_app_uid),
        getter=getters.application_menu_getter,
        state=OwnerSG.application_menu
    ),
)