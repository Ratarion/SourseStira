import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from app.bot.utils.translate import ALL_TEXTS
from app.repositories.laundry_repo import get_all_users_with_tg

# Рекомендуется настроить логгер в основном приложении:
# logging.basicConfig(level=logging.INFO)

async def broadcast_slot_freed(bot: Bot, booking_data: dict, exclude_tg_id: int = None):
    """
    Рассылает уведомление об освободившемся слоте всем пользователям с учетом их языка.

    booking_data ожидает ключи:
        - date_str: "21.12"
        - time_str: "14:00"
        - machine_type: "WASH" или "DRY" (или другие)
        - machine_num: int
    """
    users = await get_all_users_with_tg()
    count = 0

    for u in users:
        # Пропускаем исключённого пользователя
        if exclude_tg_id is not None and getattr(u, "tg_id", None) == exclude_tg_id:
            continue

        tg_id = getattr(u, "tg_id", None)
        if not tg_id:
            # Нет tg id — пропускаем
            continue

        # Безопасный выбор локали (fallback)
        lang = getattr(u, "language", None)
        t = ALL_TEXTS.get(lang) if lang else None
        if not t:
            # Попытка использовать RU, ENG или первый доступный
            t = ALL_TEXTS.get("RU") or ALL_TEXTS.get("ENG") or list(ALL_TEXTS.values())[0]

        # Определяем читаемое имя типа машины из локали
        machine_type_key = booking_data.get("machine_type", "").upper()
        if machine_type_key == "WASH":
            m_type = t.get("machine_type_wash") or t.get("machine_type") or "Wash"
        elif machine_type_key == "DRY":
            m_type = t.get("machine_type_dry") or t.get("machine_type") or "Dry"
        else:
            m_type = t.get("machine_type") or booking_data.get("machine_type", "")

        notification_text = t.get(
            "slot_freed_notification",
            "🔔 Slot available!\n\n📅 Date: {date}\n⏰ Time: {time}\n🧺 {m_type} #{m_num}\n\nBook it now!"
        ).format(
            date=booking_data.get("date_str", ""),
            time=booking_data.get("time_str", ""),
            m_type=m_type,
            m_num=booking_data.get("machine_num", "")
        )

        # Попытка отправки с обработкой rate limit
        try:
            await bot.send_message(chat_id=tg_id, text=notification_text)
            count += 1
            # Небольшая пауза между отправками, чтобы снизить риск получения RetryAfter
            await asyncio.sleep(0.1)
        except TelegramForbiddenError:
            logging.info(f"Bot forbidden by user {tg_id} — skipping.")
            continue
        except TelegramRetryAfter as e:
            # Когда получили RetryAfter — ждём указанное время и пробуем ещё раз для текущего пользователя
            logging.warning(f"RetryAfter for {tg_id}, sleeping {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=tg_id, text=notification_text)
                count += 1
            except TelegramForbiddenError:
                logging.info(f"Bot forbidden by user {tg_id} on retry — skipping.")
            except Exception as e2:
                logging.error(f"Failed to send after retry to {tg_id}: {e2}")
        except Exception as e:
            logging.error(f"Broadcast error for {tg_id}: {e}")

    logging.info(f"Broadcast finished. Sent to {count} users.")
