import datetime
from typing import Literal, List

from sqlalchemy import BigInteger, VARCHAR, ForeignKey, DateTime, Boolean, Column, Integer, String, func, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AdminsTable(Base):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(VARCHAR)
    name: Mapped[str] = mapped_column(VARCHAR)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    entry: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())
    rate: Mapped[Literal['standart', 'full']] = mapped_column(VARCHAR, default=None, nullable=True)
    sub: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), nullable=True, default=None)
    bot: Mapped["BotsTable"] = relationship("BotsTable", lazy="selectin", cascade='all, delete')


class BotsTable(Base):
    __tablename__ = 'bots'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner: Mapped[int] = mapped_column(ForeignKey('admins.user_id', ondelete='CASCADE'))
    token: Mapped[str] = mapped_column(VARCHAR, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    users: Mapped[List["UsersTable"]] = relationship('UsersTable', lazy="selectin",cascade='all, delete', uselist=True)
    deeplinks: Mapped[List["DeeplinksTable"]] = relationship('DeeplinksTable', lazy="selectin", cascade='all, delete', uselist=True)


class UsersTable(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    bot: Mapped[str] = mapped_column(ForeignKey('bots.token', ondelete='CASCADE'))
    username: Mapped[str] = mapped_column(VARCHAR)
    name: Mapped[str] = mapped_column(VARCHAR)
    user_id: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[int] = mapped_column(Integer, default=1)
    activity: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())
    entry: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())


class ApplicationsTable(Base):
    __tablename__ = 'applications'

    uid_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    receiver: Mapped[str] = mapped_column(VARCHAR)
    amount: Mapped[int] = mapped_column(Integer)
    rub: Mapped[int] = mapped_column(Integer)
    usdt: Mapped[float] = mapped_column(Float)
    create: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())
    status: Mapped[Literal[0, 1, 2]] = mapped_column(Integer, default=1)
    """
    0 - Не оплачен
    1 - в процессе оплаты
    2 - Оплачен
    3 - Ошибка выполнения
    """
    payment: Mapped[Literal['sbp', 'card', 'crypto_bot', 'crypto']] = mapped_column(VARCHAR, default=None, nullable=True)
    type: Mapped[Literal['stars', 'premium', 'ton']] = mapped_column(VARCHAR, default=None, server_default=None, nullable=True)


class DeeplinksTable(Base):
    __tablename__ = 'deeplinks'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    bot: Mapped[str] = mapped_column(ForeignKey('bots.token', ondelete='CASCADE'))
    link: Mapped[str] = mapped_column(VARCHAR)
    entry: Mapped[int] = mapped_column(BigInteger, default=0)


class BotStatic(Base):
    __tablename__ = 'bot-static'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bot: Mapped[str] = mapped_column(ForeignKey('bots.token', ondelete='CASCADE'))
    payments: Mapped[int] = mapped_column(BigInteger, default=0)
    buys: Mapped[int] = mapped_column(BigInteger, default=0)
    earn: Mapped[int] = mapped_column(Integer, default=0)
    charge: Mapped[int] = mapped_column(Integer, default=15)


class GeneralStatic(Base):
    __tablename__ = 'general-static'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    buys: Mapped[int] = mapped_column(BigInteger, default=0)
    sum: Mapped[int] = mapped_column(BigInteger, default=0)
    earn: Mapped[int] = mapped_column(Integer, default=0)
    standard: Mapped[int] = mapped_column(Integer, default=0)
    standard_buys: Mapped[int] = mapped_column(Integer, default=0)
    full: Mapped[int] = mapped_column(Integer, default=0)
    full_buys: Mapped[int] = mapped_column(Integer, default=0)

