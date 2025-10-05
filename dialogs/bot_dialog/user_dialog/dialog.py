from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.bot_dialog.user_dialog import getters

from states.state_groups import startSG

user_dialog = Dialog(
    Window(
        #DynamicMedia('media'),
        Const('<b>✨ Добро пожаловать!</b>\n\n'
              'Здесь можно приобрести Премиум, TON и Telegram звезды без верификации KYC и дешевле чем в приложении.'),
        Button(Const('⭐️Купить звезды'), id='stars_choose', on_click=getters.buy_choose),
        Row(
            #Button(Const('🪙TON'), id='ton_choose', on_click=getters.buy_choose),
            Button(Const('👑Премиум'), id='premium_choose', on_click=getters.buy_choose)
        ),
        Column(
            SwitchTo(Const('📋Правила'), id='rules_menu_switcher', state=startSG.rules_menu),
            #Url(Const('📩Поддержка'), id='support_url', url=Const('https://t.me/TrustStarsHelp')),
        ),
        state=startSG.start
    ),
    Window(
        Format('Отправьте юзернейм пользователя, которому будем дарить {present}\n\n'
               '❗️<em>Проверьте, что аккаунт существует.</em>'),
        TextInput(
            id='get_username',
            on_success=getters.get_username
        ),
        Button(Const('Покупаю себе'), id='skip_get_username', on_click=getters.skip_get_username),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        getter=getters.get_username_getter,
        state=startSG.get_username
    ),
    Window(
        Const('🪙Выберите способ получения TON:'),
        Column(
            SwitchTo(Const('👤Аккаунт Telegram'), id='get_username_switcher', state=startSG.get_username),
            #Button(Const('👝TON кошелек (скоро будет)'), id='get_address_switcher')  # state=startSG.get_address
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        state=startSG.ton_receipt_menu
    ),
    Window(
        Const('Отправьте адрес TON кошелька, на который будем отправлять TON'),
        state=startSG.get_address
    ),
    Window(
        Format('<b>👤Получатель:</b> {username}'),
        Const('⭐️Отправьте количество звезд для покупки <em>(минимум 50)</em>'),
        TextInput(
            id='get_stars_amount',
            on_success=getters.get_stars_amount
        ),
        SwitchTo(Const('🔙Назад'), id='back_get_username', state=startSG.get_username),
        getter=getters.get_rate_amount_getter,
        state=startSG.get_stars_amount
    ),
    Window(
        Format('<b>👤Получатель:</b> {username}'),
        Const('👑Выберите кол-во месяцев для покупки'),
        Column(
            Button(Const('3 месяца'), id='3_months_choose', on_click=getters.premium_rate_choose),
            Button(Const('6 месяцев'), id='6_months_choose', on_click=getters.premium_rate_choose),
            Button(Const('12 месяцев'), id='12_months_choose', on_click=getters.premium_rate_choose),
        ),
        SwitchTo(Const('🔙Назад'), id='back_get_username', state=startSG.get_username),
        getter=getters.get_rate_amount_getter,
        state=startSG.get_premium_rate
    ),
    Window(
        Format('<b>👤Получатель:</b> {username}', when='username'),
        Format('<b>Адрес получателя: </b> {address}', when='address'),
        Const('🪙Введите кол-во TON для покупки <em>(от 1 до 100 TON)</em>'),
        TextInput(
            id='get_ton_amount',
            on_success=getters.get_ton_amount
        ),
        SwitchTo(Const('🔙Назад'), id='back_ton_receipt_menu', state=startSG.ton_receipt_menu),
        getter=getters.get_rate_amount_getter,
        state=startSG.get_ton_amount
    ),
    Window(
        Format('{text}'),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        getter=getters.rules_menu_getter,
        state=startSG.rules_menu
    ),
)