from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Integer, DateTime, String
from datetime import datetime
from app.db.base import Base

class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inidresidents: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Переименовано для соответствия схеме
    inidmachine: Mapped[int] = mapped_column(Integer, nullable=False)  # Обратите внимание: в схеме indimachine (не inidmachine)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)  # Добавьте это для соответствия схеме