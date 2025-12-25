import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.repositories.laundry_repo import (
    get_bookings_to_remind,
    set_booking_status,
    get_expired_unconfirmed_bookings,
    cancel_booking
)
from app.bot.utils.translate import ALL_TEXTS
from app.bot.utils.broadcaster import broadcast_slot_freed

scheduler = AsyncIOScheduler()

async def check_confirmations(bot: Bot):
    """
    1. Находит записи за 40 минут до начала -> шлет кнопку "Подтвердить".
    2. Находит записи за 30 минут до начала (которые не подтвердили) -> отменяет.
    """
    
    # --- ЭТАП 1: Рассылка напоминаний (за 40 минут) ---
    bookings_to_remind = await get_bookings_to_remind(minutes_before=60)
    for b in bookings_to_remind:
        if not b.user or not b.user.tg_id:
            continue
            
        lang = b.user.language
        t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
        
        # Клавиатура подтверждения
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t["confirm_btn"], callback_data=f"confirm_{b.id}")]
        ])
        
        try:
            await bot.send_message(
                b.user.tg_id,
                t["confirm_booking_prompt"].format(time=b.start_time.strftime("%H:%M")),
                reply_markup=kb
            )
            # Ставим статус, что ждем подтверждения
            await set_booking_status(b.id, "wait_confirm")
            logging.info(f"Sent confirmation request for booking {b.id}")
        except Exception as e:
            logging.error(f"Failed to send confirm req to {b.user.tg_id}: {e}")

    # --- ЭТАП 2: Авто-отмена (за 30 минут) ---
    expired = await get_expired_unconfirmed_bookings(minutes_before_deadline=30)
    for b in expired:
        # 1. Отменяем в БД (удаляем)
        await cancel_booking(b.id)
        logging.info(f"Autocanceled booking {b.id} due to no confirmation")
        
        # 2. Уведомляем владельца
        if b.user and b.user.tg_id:
            lang = b.user.language
            t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
            try:
                await bot.send_message(
                    b.user.tg_id,
                    t["booking_autocanceled"].format(time=b.start_time.strftime("%H:%M"))
                )
            except:
                pass

        # 3. Рассылаем всем остальным, что слот свободен
        booking_data = {
            "date_str": b.start_time.strftime("%d.%m"),
            "time_str": b.start_time.strftime("%H:%M"),
            "machine_type": b.machine.type_machine,
            "machine_num": b.machine.number_machine
        }
        # Запускаем рассылку в фоне
        asyncio.create_task(broadcast_slot_freed(bot, booking_data, exclude_tg_id=b.user.tg_id))

def start_scheduler(bot: Bot):
    scheduler.add_job(check_confirmations, 'interval', minutes=1, kwargs={"bot": bot})
    scheduler.start()