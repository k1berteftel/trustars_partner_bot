from aiogram.types import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Next, Url
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.start_dialog import getters
from states.state_groups import InitialSG


start_dialog = Dialog(
    Window(
        Const('Для начала давайте создадим <b>вашего бота</b>'),
        Next(Const('🔥Начать'), id='get_token_switcher'),
        state=InitialSG.start
    ),
    Window(
        Const('Отправьте токен бота из @BotFather'),
        TextInput(
            id='get_token',
            on_success=getters.get_token
        ),
        Column(
            Url(Const('📝Инструкция'), id='manual_url', url=Const('https://telegra.ph/Instrukciya-po-sozdaniyu-tokena-cherez-BotFather-10-09')),
        ),
        state=InitialSG.get_token
    ),
)