from aiogram.fsm.state import State, StatesGroup

# Обычная группа состояний


class adminSG(StatesGroup):
    start = State()

    get_mail = State()
    get_time = State()
    get_keyboard = State()
    confirm_mail = State()

    deeplink_menu = State()
    deeplink_del = State()

    set_charge = State()

    get_derive_amount = State()


class InitialSG(StatesGroup):
    start = State()
    get_token = State()


class startSG(StatesGroup):
    start = State()

    get_username = State()
    ton_receipt_menu = State()
    get_ton_amount = State()
    get_address = State()
    get_stars_amount = State()
    get_premium_rate = State()

    rules_menu = State()


class PaymentSG(StatesGroup):
    menu = State()
    process_payment = State()


class OwnerSG(StatesGroup):
    start = State()

    get_admin_data = State()
    rate_choose = State()

