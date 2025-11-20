from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import BigInteger
from db.models import base

class rooms(base):
    __tablename__ = "rooms"
    idRoom: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    