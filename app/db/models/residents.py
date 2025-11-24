from sqlalchemy import String, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inidroom: Mapped[int] = mapped_column(Integer, nullable=False)
    idcards: Mapped[int] = mapped_column(Integer, nullable=False)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    patronymic: Mapped[str] = mapped_column(String, nullable=False)