from dialogs.bot_dialog.payment_dialog.dialog import payment_dialog
from dialogs.bot_dialog.user_dialog.dialog import user_dialog


def get_bot_dialogs():
    return [user_dialog, payment_dialog]