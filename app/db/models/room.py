from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class rooms(Base):
    __tablename__ = "rooms"
    idRoom: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    