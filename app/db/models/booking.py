from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import Boolean, Integer, DateTime
from datetime import datetime
from app.db.base import Base


class booking(Base):
    __tablename__ = "booking"

    # autoincrement=True добавит автоматический номер
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    iniduser: Mapped[int] = mapped_column(Integer, nullable=False)
    inidmachine: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
