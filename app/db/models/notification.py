from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_residents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_booking: Mapped[int] = mapped_column(BigInteger, nullable=True)
    create_date: Mapped[datetime] = mapped_column(DateTime, default=datetime)
    description: Mapped[str] = mapped_column(String, nullable=False)