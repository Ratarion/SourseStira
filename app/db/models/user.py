from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, BigInteger, Boolean
from datetime import datetime
from db.models import base
from db.models import room 

class users(base):
    __tablename__ = "users"

    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inIdRoom: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, nullable=False)
    idCards: Mapped[BigInteger] = mapped_column(BigInteger, primary_key = True, nullable=False)
    tg_id: Mapped[BigInteger] = mapped_column(BigInteger, unique=True, nullable=False)
    last_name: Mapped[String] = mapped_column(String, nullable=False)
    first_name: Mapped[String] = mapped_column(String, nullable=False)
    patronymic: Mapped[String] = mapped_column(String, nullable=False)
    is_registered: Mapped[Boolean] = mapped_column(Boolean, default=False, nullable=False)
