from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
import os
import psycopg2

# Load environment variables from .env
load_dotenv()

# Получаем строку подключения
DATABASE_URL = os.getenv("DATABASE_URL")

# === СИНХРОННОЕ ПОДКЛЮЧЕНИЕ ДЛЯ ПРОВЕРКИ ===
def test_connection():
    """Проверка подключения к базе данных"""
    try:
        connection = psycopg2.connect(DATABASE_URL)
        print("✅ Connection to Supabase successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

# === АСИНХРОННОЕ ПОДКЛЮЧЕНИЕ ДЛЯ SQLAlchemy ===
# Заменяем на asyncpg для асинхронной работы
if DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    # Fallback на SQLite если DATABASE_URL не установлен
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./app/db/database.db"

# Создаем асинхронный движок
engine = create_async_engine(ASYNC_DATABASE_URL)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def init_db():
    # Сначала тестируем подключение
    test_connection()
    
    # Затем создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully!")