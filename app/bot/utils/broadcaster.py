import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from app.bot.utils.translate import ALL_TEXTS
from app.repositories.laundry_repo import get_all_users_with_tg

async def broadcast_slot_freed(bot: Bot, booking_data: dict, exclude_tg_id: int = None):
    """
    Рассылает уведомление об освободившемся слоте всем пользователям с учетом их языка.
    
    :param booking_data: словарь {
        "date_str": "21.12",
        "time_str": "14:00",
        "machine_type": "WASH" или "DRY",
        "machine_num": 1
    }
    :param exclude_tg_id: ID пользователя, которому НЕ надо слать (кто отменил)
    """
    users = await get_all_users_with_tg()
    count = 0

    for u in users:
        # 1. Пропускаем того, кто отменил запись (ему не нужно уведомление о его же отмене)
        if exclude_tg_id and u.tg_id == exclude_tg_id:
            continue

        # 2. ОПРЕДЕЛЯЕМ ЯЗЫК ПОЛУЧАТЕЛЯ
        lang = u.language if u.language else "RU" # Если языка нет, по дефолту RU
        target_t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
        
        # 3. Локализация типа машины (Стирка/Сушка) для получателя
        if booking_data["machine_type"] == "WASH":
            m_type_str = target_t.get("machine_type_wash", "Стирка")
        else:
            m_type_str = target_t.get("machine_type_dry", "Сушка")

        # 4. Формируем текст
        try:
            notification_text = target_t["slot_freed_notification"].format(
                date=booking_data["date_str"],
                time=booking_data["time_str"],
                m_type=m_type_str,
                m_num=booking_data["machine_num"]
            )
            
            # 5. Отправляем
            await bot.send_message(chat_id=u.tg_id, text=notification_text)
            count += 1
            await asyncio.sleep(0.05) # Небольшая задержка, чтобы не забанил Телеграм

        except TelegramForbiddenError:
            pass # Бот заблокирован пользователем
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=u.tg_id, text=notification_text)
            except:
                pass
        except Exception as e:
            logging.error(f"Broadcast error for {u.tg_id}: {e}")

    logging.info(f"Broadcast finished. Sent to {count} users.")