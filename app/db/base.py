# app/db/base.py
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# === АСИНХРОННАЯ ПРОВЕРКА ПОДКЛЮЧЕНИЯ ===
async def test_connection():
    """Асинхронная проверка подключения к базе данных"""
    try:
        import asyncpg
        # Парсим DATABASE_URL для asyncpg
        from urllib.parse import urlparse
        url = urlparse(DATABASE_URL)
        
        conn = await asyncpg.connect(
            host=url.hostname,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.path[1:]  # убираем первый символ '/'
        )
        print("✅ Connection to Supabase successful!")
        
        result = await conn.fetchval('SELECT NOW()')
        print("Current Time:", result)

        await conn.close()
        print("Connection closed.")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

# === АСИНХРОННОЕ ПОДКЛЮЧЕНИЕ ДЛЯ SQLAlchemy ===
if DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./app/db/database.db"

engine = create_async_engine(ASYNC_DATABASE_URL)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def init_db():
    # Тестируем подключение асинхронно
    await test_connection()
    
    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully!")