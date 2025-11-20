import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

if not find_dotenv():  # Функция поиска переменных окружения
    exit("Переменные окружения не загружены, так как отсутствует файл .env")
else:
    load_dotenv()  # Загрузка переменных окружения

root_path = Path(__file__).resolve().parents[1]

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID1 = int(os.getenv("ADMIN_ID1"))
ADMIN_ID2 = int(os.getenv("ADMIN_ID2"))
