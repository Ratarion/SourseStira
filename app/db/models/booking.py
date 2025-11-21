from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, BigInteger, Boolean, DateTime
from datetime import datetime
from app.db.base import Base
from . import user
from . import machine

class booking(Base):
    __tablename__ = "booking"

    # autoincrement=True добавит автоматический номер
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    inIdUser: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    inIdMachine: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
