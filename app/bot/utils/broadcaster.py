# broadcaster.py (полный обновленный код)

import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from app.bot.utils.translate import ALL_TEXTS
from app.repositories.laundry_repo import get_all_users_with_tg
from app.bot.keyboards import get_exit_keyboard  # <--- ДОБАВЬТЕ ИМПОРТ

async def broadcast_slot_freed(bot: Bot, booking_data: dict, exclude_tg_id: int = None):
    users = await get_all_users_with_tg()
    count = 0

    for u in users:
        if exclude_tg_id is not None and getattr(u, "tg_id", None) == exclude_tg_id:
            continue

        tg_id = getattr(u, "tg_id", None)
        if not tg_id:
            continue

        # Выбор локали
        lang = getattr(u, "language", "RU")
        t = ALL_TEXTS.get(lang) or ALL_TEXTS.get("RU")

        # 1. Исправление типа машины (база хранит "Стиральная"/"Сушильная")
        raw_type = booking_data.get("machine_type", "")
        if raw_type == "Стиральная":
            m_type = t.get("machine_type_wash", "Стиральная")
        elif raw_type == "Сушильная":
            m_type = t.get("machine_type_dry", "Сушильная")
        else:
            m_type = raw_type

        # 2. Исправление времени (используем ключи из scheduler.py)
        # Формируем интервал: "14:00 – 15:30"
        time_range = f"{booking_data.get('start_time_str')} – {booking_data.get('end_time_str')}"

        # Формируем текст (включаем parse_mode="HTML" для поддержки <b> из словарей)
        notification_text = t.get(
            "slot_freed_notification",
            "🔔 <b>Slot available!</b>\n\n📅 Date: {date}\n⏰ Time: {time}\n🧺 {m_type} #{m_num}"
        ).format(
            date=booking_data.get("date_str", ""),
            time=time_range,  # Передаем сформированную строку
            m_type=m_type,
            m_num=booking_data.get("machine_num", "")
        )

        try:
            await bot.send_message(
                chat_id=tg_id, 
                text=notification_text, 
                parse_mode="HTML",
                reply_markup=get_exit_keyboard(lang)  # <--- ДОБАВЛЕНО: Клавиатура с кнопкой
            )
            count += 1
            await asyncio.sleep(0.05) 
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except TelegramForbiddenError:
            logging.warning(f"User {tg_id} blocked the bot.")
        except Exception as e:
            logging.error(f"Error sending to {tg_id}: {e}")

    logging.info(f"Broadcast finished. Sent to {count} users.")