from sqlalchemy import String, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base

class users(Base):
    __tablename__ = "users"

    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inIdRoom: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, nullable=False)
    idCards: Mapped[BigInteger] = mapped_column(BigInteger, primary_key = True, nullable=False)
    tg_id: Mapped[BigInteger] = mapped_column(BigInteger, unique=True, nullable=False)
    last_name: Mapped[String] = mapped_column(String, nullable=False)
    first_name: Mapped[String] = mapped_column(String, nullable=False)
    patronymic: Mapped[String] = mapped_column(String, nullable=False)
