from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, BigInteger, Boolean
from datetime import datetime
from db.models import base
from db.models import room 

class machines(base):
    __tablename__ = "machines"

    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type_machine: Mapped[String] = mapped_column(String, nullable=False)
    number_machine: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    status: Mapped[Boolean] = mapped_column(Boolean, default=False, nullable=False)

    