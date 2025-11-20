from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot

from app.config import config as cfg

user_router = Router(name="user_router")
bot = Bot(token=cfg.BOT_TOKEN)


@user_router.message(Command('start'))
async def welcome_message(msg: Message):
    
    if msg.from_user.id == cfg.ADMIN_ID1 and msg.from_user.id == cfg.ADMIN_ID2:

        await msg.answer("<b>Добро пожаловать!</b>\n\n Админ бота для управления стиркой.")