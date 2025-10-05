import datetime
from typing import Literal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, insert, update, column, text, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.model import (UsersTable, DeeplinksTable, AdminsTable, ApplicationsTable, BotsTable,
                            BotStatic, GeneralStatic, PricesTable)


async def setup_database(session: async_sessionmaker):
    async with session() as session:
        if not await session.scalar(select(GeneralStatic)):
            await session.execute(insert(GeneralStatic).values(
            ))
        if not await session.scalar(select(PricesTable)):
            await session.execute(insert(PricesTable).values(
            ))
        await session.commit()


class DataInteraction():
    def __init__(self, session: async_sessionmaker, token: str | None):
        self._sessions = session
        self._token = token

    async def check_user(self, user_id: int) -> bool:
        async with self._sessions() as session:
            result = await session.scalar(select(UsersTable).where(
                and_(
                    UsersTable.user_id == user_id,
                    UsersTable.bot == self._token
                )
            )
            )
        return True if result else False

    async def check_bot(self):
        async with self._sessions() as session:
            result = await session.scalar(select(BotsTable).where(BotsTable.token == self._token))
        return bool(result)

    async def add_user(self, user_id: int, username: str, name: str):
        if await self.check_user(user_id):
            return
        async with self._sessions() as session:
            await session.execute(insert(UsersTable).values(
                bot=self._token,
                user_id=user_id,
                username=username,
                name=name,
            ))
            await session.commit()

    async def add_entry(self, link: str):
        async with self._sessions() as session:
            await session.execute(update(DeeplinksTable).where(DeeplinksTable.link == link).values(
                entry=DeeplinksTable.entry+1
            ))
            await session.commit()

    async def add_deeplink(self, link: str):
        async with self._sessions() as session:
            await session.execute(insert(DeeplinksTable).values(
                bot=self._token,
                link=link
            ))
            await session.commit()

    async def add_bot_static(self, token: str):
        async with self._sessions() as session:
            await session.execute(insert(BotStatic).values(
                bot=token
            ))
            await session.commit()

    async def add_bot(self, user_id: int, token: str) -> bool:
        async with self._sessions() as session:
            if await self.check_bot():
                return False
            await session.execute(insert(BotsTable).values(
                owner=user_id,
                token=token
            ))
            await session.commit()
        await self.add_bot_static(token)
        return True

    async def add_admin(self, user_id: int, username: str, name: str):
        async with self._sessions() as session:
            if await self.get_admin(user_id):
                return
            await session.execute(insert(AdminsTable).values(
                user_id=user_id,
                username=username,
                name=name,
            ))
            await session.commit()

    async def add_payment(self):
        async with self._sessions() as session:
            await session.execute(update(BotStatic).where(BotStatic.bot == self._token).values(
                payments=BotStatic.payments + 1
            ))
            await session.commit()

    async def add_buys(self, sum: int):
        async with self._sessions() as session:
            await session.execute(update(BotStatic).where(BotStatic.bot == self._token).values(
                buys=BotStatic.buys + sum
            ))
            await session.commit()

    async def add_application(self, user_id: int, receiver: str,
                              amount: int, rub: int, usdt: float, buy: Literal['stars', 'premium', 'ton'], count=1) -> ApplicationsTable:
        applications = await self.get_applications()
        uid_key = applications[-1].uid_key + count if applications else 1000
        async with self._sessions() as session:
            try:
                await session.execute(insert(ApplicationsTable).values(
                    uid_key=uid_key,
                    user_id=user_id,
                    receiver=receiver,
                    amount=amount,
                    rub=rub,
                    usdt=usdt,
                    type=buy
                ))
                await session.commit()
            except Exception:
                return await self.add_application(user_id, receiver, amount, rub, usdt, buy, count+1)
            return await self.get_application(uid_key)

    async def get_applications(self):
        async with self._sessions() as session:
            result = await session.scalars(select(ApplicationsTable).order_by(ApplicationsTable.uid_key))
        return result.fetchall()

    async def get_application(self, uid_key: int):
        async with self._sessions() as session:
            result = await session.scalar(select(ApplicationsTable).where(ApplicationsTable.uid_key == uid_key))
        return result

    async def get_receiver_applications(self, receiver: str):
        async with self._sessions() as session:
            result = await session.scalars(select(ApplicationsTable).where(ApplicationsTable.receiver == receiver))
        return result.fetchall()

    async def get_last_application(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(ApplicationsTable).where(ApplicationsTable.user_id == user_id)
                                          .order_by(ApplicationsTable.create.desc()))
        return result

    async def get_bots(self):
        async with self._sessions() as session:
            result = await session.scalars(select(BotsTable))
        return result.fetchall()

    async def get_bot_by_id(self, bot_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(BotsTable).where(BotsTable.id == bot_id))
        return result

    async def get_bot_by_token(self, token: str):
        async with self._sessions() as session:
            result = await session.scalar(select(BotsTable).where(BotsTable.token == token))
        return result

    async def get_users(self):
        async with self._sessions() as session:
            result = await session.scalars(select(UsersTable).where(UsersTable.bot == self._token))
        return result.fetchall()

    async def get_user(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(UsersTable).where(and_(
                    UsersTable.user_id == user_id,
                    UsersTable.bot == self._token
                )
            ))
        return result

    async def get_user_by_username(self, username: str):
        async with self._sessions() as session:
            result = await session.scalar(select(UsersTable).where(and_(
                    UsersTable.username == username,
                    UsersTable.bot == self._token
                )
            ))
        return result

    async def get_bot_static(self):
        async with self._sessions() as session:
            result = await session.scalar(select(BotStatic).where(BotStatic.bot == self._token))
        return result

    async def get_admins(self):
        async with self._sessions() as session:
            result = await session.scalars(select(AdminsTable))
        return result.fetchall()

    async def get_admin(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(AdminsTable).where(AdminsTable.user_id == user_id))
        return result

    async def get_deeplinks(self):
        async with self._sessions() as session:
            result = await session.scalars(select(DeeplinksTable).where(DeeplinksTable.bot == self._token))
        return result.fetchall()

    async def get_prices(self):
        async with self._sessions() as session:
            result = await session.scalar(select(PricesTable))
        return result

    async def update_admin_sub(self, user_id: int, months: int | None):
        sub = None
        new = False
        if isinstance(months, int):
            user = await self.get_admin(user_id)
            if user.sub:
                sub = user.sub + relativedelta(months=months)
            else:
                new = True
                sub = datetime.datetime.now() + relativedelta(months=months)
        async with self._sessions() as session:
            await session.execute(update(AdminsTable).where(AdminsTable.user_id == user_id).values(
                sub=sub
            ))
            await session.commit()
        return new

    async def update_application(self, uid_key: int, status: int, payment: str | None):
        async with self._sessions() as session:
            await session.execute(update(ApplicationsTable).where(ApplicationsTable.uid_key == uid_key).values(
                status=status,
                payment=payment
            ))
            await session.commit()

    async def update_username(self, user_id: int, username: str):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(and_(
                UsersTable.user_id == user_id,
                UsersTable.bot == self._token
            )).values(
                username=username
            ))
            await session.commit()

    async def set_charge(self, **kwargs):
        async with self._sessions() as session:
            await session.execute(update(PricesTable).values(
                kwargs
            ))
            await session.commit()

    async def set_activity(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(and_(
                UsersTable.user_id == user_id,
                UsersTable.bot == self._token
            )).values(
                activity=datetime.datetime.today()
            ))
            await session.commit()

    async def set_active(self, user_id: int, active: int):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(and_(
                UsersTable.user_id == user_id,
                UsersTable.bot == self._token
            )).values(
                active=active
            ))
            await session.commit()

    async def set_bot_active(self, status: bool):
        async with self._sessions() as session:
            await session.execute(update(BotsTable).where(BotsTable.token == self._token).values(
                active=status
            ))
            await session.commit()

    async def del_application(self, uid_key: int):
        async with self._sessions() as session:
            await session.execute(delete(ApplicationsTable).where(ApplicationsTable.uid_key == uid_key))
            await session.commit()

    async def del_deeplink(self, link: str):
        async with self._sessions() as session:
            await session.execute(delete(DeeplinksTable).where(DeeplinksTable.link == link))
            await session.commit()

    async def del_admin(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(delete(AdminsTable).where(AdminsTable.user_id == user_id))
            await session.commit()