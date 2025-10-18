import asyncio
import datetime
import hmac
import hashlib
from aiohttp import ClientSession

from aiocryptopay import AioCryptoPay, Networks

from config_data.config import Config, load_config


config: Config = load_config()
crypto_bot = AioCryptoPay(token=config.crypto_bot.token, network=Networks.MAIN_NET)


def _get_signature(data: dict, api_key: str):
    print('data before', data)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[0]))
    print('data after ', sorted_data)
    message = '|'.join(str(v) for v in sorted_data.values())
    print(message)
    signature = hmac.new(
        key=api_key.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    sorted_data['signature'] = signature
    return sorted_data


async def get_freekassa_card(user_id: int, amount: int, app_id: int, bot_id: int):
    url = 'https://api.fk.life/v1/orders/create'
    data = {
        'shopId': 66457,
        'nonce': int(datetime.datetime.today().timestamp()),
        'us_userId': str(user_id),
        'us_appId': str(app_id),
        'us_botId': str(bot_id),
        'i': 36,
        'email': f'{user_id}@telegram.org',
        'ip': '5.35.91.55',
        'amount': str(amount),
        'currency': 'RUB'
    }
    data = _get_signature(data, config.freekassa.api_key)
    async with ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'url': data['location'],
    }


async def get_freekassa_sbp(user_id: int, amount: int, app_id: int, bot_id: int):
    url = 'https://api.fk.life/v1/orders/create'
    data = {
        'shopId': 66457,
        'nonce': int(datetime.datetime.today().timestamp()),
        'us_userId': str(user_id),
        'us_appId': str(app_id),
        'us_botId': str(bot_id),
        'i': 44,
        'email': f'{user_id}@telegram.org',
        'ip': '5.35.91.55',
        'amount': str(amount),
        'currency': 'RUB'
    }
    data = _get_signature(data, config.freekassa.api_key)
    async with ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'url': data['location'],
    }


async def get_oxa_payment_data(amount: int | float):
    usdt_rub = await _get_usdt_rub()
    amount = round(amount / usdt_rub, 2)
    url = 'https://api.oxapay.com/v1/payment/invoice'
    headers = {
        'merchant_api_key': config.oxa.api_key,
        'Content-Type': 'application/json'
    }
    data = {
        'amount': float(amount),
        'mixed_payment': False
    }
    async with ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
            data = await resp.json()
            print(data)
            print(type(data['status']), data['status'])
            if data['status'] == 429:
                print('status', data['status'])
                return await get_oxa_payment_data(amount)
    return {
        'url': data['data']['payment_url'],
        'id': data['data']['track_id']
    }


async def get_crypto_payment_data(amount: int | float):
    usdt_rub = await _get_usdt_rub()
    amount = round(amount / (usdt_rub), 2)
    invoice = await crypto_bot.create_invoice(asset='USDT', amount=amount)
    return {
        'url': invoice.bot_invoice_url,
        'id': invoice.invoice_id
    }


async def check_crypto_payment(invoice_id: int) -> bool:
    invoice = await crypto_bot.get_invoices(invoice_ids=invoice_id)
    if invoice.status == 'paid':
        return True
    return False


async def check_oxa_payment(track_id: str, counter: int = 1) -> bool:
    url = 'https://api.oxapay.com/v1/payment/' + track_id
    headers = {
        'merchant_api_key': config.oxa.api_key,
        'Content-Type': 'application/json'
    }
    async with ClientSession() as session:
        async with session.get(url, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                print('oxa check error', await resp.json())
                return False
            try:
                data = await resp.json()
            except Exception:
                if counter >= 5:
                    return False
                return await check_oxa_payment(track_id, counter+1)
    if data['data']['status'] == 'paid':
        return True
    return False


async def _get_usdt_rub() -> float:
    url = 'https://open.er-api.com/v6/latest/USD'
    async with ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
            rub = data['rates']['RUB']
    return float(rub)


async def _get_ton_usdt() -> float:
    url = 'https://api.coingecko.com/api/v3/coins/the-open-network'
    async with ClientSession() as session:
        async with session.get(url) as res:
            resp = await res.json()
            ton = float(resp['market_data']['current_price']['usd'])
    return ton


#print(asyncio.run(get_freekassa_card(23523532, 100, 1013, 2)))