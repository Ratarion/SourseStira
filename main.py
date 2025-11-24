import aiohttp
import asyncio
import logging
import sys
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

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

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"[Bot] Starting polling, attempt    {attempt}")
            await dp.start_polling(bot)
            break
        except (aiohttp.ClientConnectorError, TelegramNetworkError) as e:
            logging.error(f"[Bot] Network error on attempt {attempt}: {e}")
            if attempt < max_retries:
                wait_time = 10 * attempt
                logging.info(f"[Bot] Retrying after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error("[Bot] Max retries reached, exiting.")
                raise
        except Exception as exc:
            logging.error(f"[Bot] Unexpected error: {exc}")
            raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Bot] Бот остановлен")
