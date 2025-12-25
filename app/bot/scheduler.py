import asyncio
import logging
from datetime import datetime
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


async def _safe_create_task(coro):
    """
    Обёртка для asyncio.create_task с логированием исключений,
    чтобы фоновые задачи не "глотали" ошибки без следа.
    """
    task = asyncio.create_task(coro)

    def _task_done(t):
        try:
            exc = t.exception()
            if exc:
                logging.error(f"Background task exception: {exc}")
        except asyncio.CancelledError:
            logging.info("Background task cancelled")

    task.add_done_callback(_task_done)
    return task


async def check_confirmations(bot: Bot):
    """
    1) Находит записи за 40 минут до начала и рассылает запрос на подтверждение (кнопка).
    2) Находит записи за 30 минут до начала, которые не подтверждены -> автo-отмена.
    На ответ даеться 10 минут
    """
    now = datetime.now()
    logging.debug(f"check_confirmations run at {now.isoformat()}")

    # --- ЭТАП 1: Рассылка запросов на подтверждение (за 40 минут) ---
    try:
        bookings_to_remind = await get_bookings_to_remind(minutes_before=40)
    except Exception as e:
        logging.error(f"Failed to fetch bookings_to_remind: {e}")
        bookings_to_remind = []

    for b in bookings_to_remind:
        # Защита от некорректных данных
        user = getattr(b, "user", None)
        if not user or not getattr(user, "tg_id", None):
            continue

        # Выбираем локаль; fallback на RU/ENG/первую
        lang = getattr(user, "language", None)
        t = ALL_TEXTS.get(lang) if lang else None
        if not t:
            t = ALL_TEXTS.get("RU") or ALL_TEXTS.get("ENG") or list(ALL_TEXTS.values())[0]

        # Формируем клавиатуру подтверждения
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t.get("confirm_btn", "Confirm"), callback_data=f"confirm_{b.id}")]
        ])

        # Форматируем дату/время (подстраховка: поддержка timezone-aware datetime вне рамок этого патча)
        try:
            time_str = b.start_time.strftime("%H:%M")
            datetime_str = b.start_time.strftime("%d.%m %H:%M")
        except Exception:
            # Если start_time нестандартный — приводим через str()
            time_str = str(getattr(b, "start_time", ""))
            datetime_str = time_str

        confirm_text = t.get("confirm_booking_prompt",
                             "Please confirm your booking scheduled for {datetime} (start at {time}).").format(
            datetime=datetime_str,
            time=time_str
        )

        try:
            await bot.send_message(user.tg_id, confirm_text, reply_markup=kb)
            # Обновляем статус записи на ожидание подтверждения
            try:
                await set_booking_status(b.id, "Ожидание")
            except Exception as e:
                logging.error(f"Failed to set booking status wait_confirm for {b.id}: {e}")
            logging.info(f"Sent confirmation request for booking {b.id} to {user.tg_id}")
            # небольшая пауза между отправками
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Failed to send confirm request to {getattr(user, 'tg_id', None)}: {e}")
            continue

    # --- ЭТАП 2: Авто-отмена (за 30 минут) ---
    try:
        expired = await get_expired_unconfirmed_bookings(minutes_before_deadline=30)
    except Exception as e:
        logging.error(f"Failed to fetch expired unconfirmed bookings: {e}")
        expired = []

    for b in expired:
        try:
            await cancel_booking(b.id)
            logging.info(f"Autocanceled booking {b.id} due to no confirmation")
        except Exception as e:
            logging.error(f"Failed to cancel booking {b.id}: {e}")
            continue

        # Уведомление владельцу (если есть)
        user = getattr(b, "user", None)
        if user and getattr(user, "tg_id", None):
            lang = getattr(user, "language", None)
            t = ALL_TEXTS.get(lang) if lang else None
            if not t:
                t = ALL_TEXTS.get("RU") or ALL_TEXTS.get("ENG") or list(ALL_TEXTS.values())[0]

            try:
                time_str = b.start_time.strftime("%H:%M")
                datetime_str = b.start_time.strftime("%d.%m %H:%M")
            except Exception:
                time_str = str(getattr(b, "start_time", ""))
                datetime_str = time_str

            try:
                await bot.send_message(user.tg_id, t.get("booking_autocanceled",
                                                         "Your booking for {datetime} ({time}) was automatically canceled.")
                                       .format(datetime=datetime_str, time=time_str))
            except Exception as e:
                logging.error(f"Failed to notify owner {user.tg_id} about autocancel: {e}")

        # 3. Рассылаем всем остальным, что слот свободен
        booking_data = {
            "date_str": b.start_time.strftime("%d.%m"),
            "time_str": b.start_time.strftime("%H:%M"),
            "machine_type": getattr(b.machine, "type_machine", "") if getattr(b, "machine", None) else "",
            "machine_num": getattr(b.machine, "number_machine", "") if getattr(b, "machine", None) else ""
        }
        # Запускаем рассылку в фоне (обёртка логирует ошибки фоновой таски)
        await _safe_create_task(broadcast_slot_freed(bot, booking_data, exclude_tg_id=getattr(user, "tg_id", None)))


def start_scheduler(bot: Bot):
    """
    Запускает планировщик. max_instances=1 и coalesce=True предотвращают
    параллельные исполнения одного job'а при долгой работе.
    """
    scheduler.add_job(
        check_confirmations,
        'interval',
        minutes=1,
        kwargs={"bot": bot},
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    logging.info("Scheduler started")
