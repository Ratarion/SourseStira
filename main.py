import asyncio, logging
import sys


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config as cfg
from app.bot.handlers import users

from app.db.base import init_db

print(sys.path)

TOKEN = cfg.BOT_TOKEN
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main():
    await init_db()
    dp.include_routers(users.user_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
       
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Bot] Бот остановлен")