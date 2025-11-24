from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class rooms(Base):
    __tablename__ = "rooms"
    
    idroom: Mapped[int] = mapped_column(Integer, primary_key=True)
    