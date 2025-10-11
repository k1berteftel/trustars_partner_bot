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
            SwitchTo(Const('Выдать подписку'), id='get_admin_data_switcher', state=OwnerSG.get_admin_data),
        ),
        Cancel(Const('Закрыть админку'), id='close_admin'),
        state=OwnerSG.start
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
)