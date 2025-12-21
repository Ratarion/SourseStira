from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, DateTime, String, ForeignKey
from datetime import datetime
from app.db.models.machine import Machine
from app.db.models.residents import Resident
from app.db.base import Base

class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inidresidents: Mapped[int] = mapped_column(BigInteger, ForeignKey("residents.id"))
    
    # Измени это поле, чтобы указать, что это внешний ключ (ForeignKey)
    inidmachine: Mapped[int] = mapped_column(Integer, ForeignKey("machines.id"), nullable=False)
    
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)

    # ДОБАВЬ ЭТУ СТРОКУ:
    # Она создает виртуальное поле .machine, которое SQLAlchemy будет подгружать
    machine: Mapped["Machine"] = relationship("Machine")
    user: Mapped["Resident"] = relationship("Resident")