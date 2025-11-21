from sqlalchemy import String, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from app.db.models import room

class machines(Base):
    __tablename__ = "machines"

    # 1. ID с автоинкрементом
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
        
    type_machine: Mapped[String] = mapped_column(String, nullable=False)
    number_machine: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    status: Mapped[Boolean] = mapped_column(Boolean, default=False, nullable=False)

    