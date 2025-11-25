from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DBNAME = os.getenv("DBNAME")

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

engine = create_async_engine(DATABASE_URL)

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass



async def init_db():
    async with engine.begin() as conn:
        # Опционально: создайте таблицы, если нужно (раскомментируйте, если хотите автоматическое создание схемы)
        # await conn.run_sync(Base.metadata.create_all)
        pass

# Функция тестирования соединения
async def test_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Соединение успешно! Результат:", result.scalar())
    except Exception as e:
        print(f"Ошибка соединения: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
