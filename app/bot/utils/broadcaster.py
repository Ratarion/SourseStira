import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from app.bot.utils.translate import ALL_TEXTS
from app.repositories.laundry_repo import get_all_users_with_tg

async def broadcast_slot_freed(bot: Bot, booking_data: dict, exclude_tg_id: int = None):
    """
    Рассылает уведомление об освободившемся слоте всем пользователям.
    
    booking_data ожидает:
        - date_str: "21.12"
        - start_time_str: "14:00"
        - end_time_str: "15:30"
        - machine_type: "Стиральная" или "Сушильная"
        - machine_num: int
    """
    users = await get_all_users_with_tg()
    count = 0

    for u in users:
        if exclude_tg_id is not None and getattr(u, "tg_id", None) == exclude_tg_id:
            continue

        tg_id = getattr(u, "tg_id", None)
        if not tg_id:
            continue

        # Локализация
        lang = getattr(u, "language", "RU")
        t = ALL_TEXTS.get(lang) or ALL_TEXTS.get("RU")

        # Сопоставление типа машины (база -> перевод)
        raw_type = booking_data.get("machine_type", "")
        if raw_type == "Стиральная":
            m_type = t.get("machine_type_wash", "Wash")
        elif raw_type == "Сушильная":
            m_type = t.get("machine_type_dry", "Dry")
        else:
            m_type = raw_type

        # Формируем строку времени
        time_range = f"{booking_data.get('start_time_str')} – {booking_data.get('end_time_str')}"

        # Получаем шаблон и форматируем
        # В переводах (ru.py/en.py) ключ slot_freed_notification должен поддерживать {time}
        notification_text = t.get(
            "slot_freed_notification",
            "🔔 Slot available!\n\n📅 Date: {date}\n⏰ Time: {time}\n🧺 {m_type} #{m_num}"
        ).format(
            date=booking_data.get("date_str", ""),
            time=time_range,
            m_type=m_type,
            m_num=booking_data.get("machine_num", "")
        )

        try:
            await bot.send_message(chat_id=tg_id, text=notification_text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05) # Лимит Telegram ~30 сообщений в секунду
        except TelegramForbiddenError:
            continue
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=tg_id, text=notification_text, parse_mode="HTML")
                count += 1
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Error sending to {tg_id}: {e}")

    logging.info(f"Broadcast finished. Sent to {count} users.")