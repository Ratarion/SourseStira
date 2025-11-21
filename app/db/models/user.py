from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class users(Base):
    __tablename__ = "users"

    #1. ID primary_key с автоинкрементом
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    

    inidroom: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idcards: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # 3. Данные телеграм
    tg_id: Mapped[BigInteger] = mapped_column(BigInteger, unique=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    patronymic: Mapped[str] = mapped_column(String, nullable=False)