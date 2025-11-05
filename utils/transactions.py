import asyncio
import aiohttp
import json
import logging

from utils.payments.create_payment import _get_ton_usdt
from config_data.config import load_config, Config


config: Config = load_config()


BASE_URL = 'https://robynhood.parssms.info/'


headers = {
    'X-API-Key': config.fragment.api_key
}


async def get_stars_price(amount: int) -> float:
    url = BASE_URL + 'api/prices'
    data = {
        'product_type': 'stars',
        'quantity': str(amount)
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=data, headers=headers, ssl=False) as resp:
            if resp.status not in [200, 201]:
                try:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'JSON получения цены: {await resp.json()}\n\n')
                except Exception:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'Content получения цены: {await resp.text()}\n\n')
                raise Exception
            data = await resp.json()
            ton = await _get_ton_usdt()
    return round(float(data['price']) * ton, 5)


async def transfer_stars(username: str, stars: int) -> bool:
    url = BASE_URL + 'api/purchase'
    data = {
        "product_type": "stars",
        "recipient": username,
        "quantity":  str(stars),
        #"idempotency_key": config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status not in [200, 201]:
                try:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'JSON транзакции:{await response.json()}\n\n')
                except Exception:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'Content транзакции:{await response.text()}\n\n')
                return False
            data = await response.json()
            print(data)
    return True


async def transfer_premium(username: str, months: int):
    url = BASE_URL + 'api/purchase'
    data = {
        "product_type": "premium",
        "recipient": username,
        "months": str(months),
        #"idempotency_key": config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status not in [200, 201]:
                try:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'JSON Premium:{await response.json()}\n\n')
                except Exception:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'Content Premium:{await response.text()}\n\n')
                return False
            data = await response.json()
            print(data)
    return True


async def transfer_ton(username: str, amount: int):
    url = 'https://tg.parssms.info/v1/ads/topup'
    data = {
        "query": username,
        "amount": str(amount)
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                print(await resp.content.read())
                logging.error(await resp.content.read())
                try:
                    logging.error(await resp.json())
                except Exception:
                    ...
                return False
            data = await resp.json()
            if data['ok'] != True:
                logging.error(data)
                return False
            print(data)
    return True


async def check_user_premium(username: str, months: int):
    url = BASE_URL + 'api/test/purchase'
    data = {
        "product_type": "premium",
        "recipient": username,
        "months": str(months),
        #"idempotency_key": config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status not in [200, 201]:
                try:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'JSON Premium:{await response.json()}\n\n')
                except Exception:
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'Content Premium:{await response.text()}\n\n')
                return False
            data = await response.json()
            print(data)
    return True



#print(asyncio.run(check_user_premium('Leggit_dev', 3)))