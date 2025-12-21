# app/bot/handlers/cancel_record.py
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_cancel_booking_keyboard, get_section_keyboard, get_back_to_sections_keyboard
from app.bot.states import CancelRecord
from app.repositories.laundry_repo import (
    get_user_by_tg_id, 
    get_user_bookings, 
    cancel_booking, 
    get_booking_by_id, 
    get_all_users_with_tg
)

cancel_record_router = Router()

@cancel_record_router.callback_query(F.data == "remove_records")
async def start_cancel_process(callback: CallbackQuery, state: FSMContext):
    """
    Показывает пользователю список его активных записей для удаления.
    """
    lang, t = await get_lang_and_texts(state)
    user = await get_user_by_tg_id(callback.from_user.id)
    
    if not user:
        await callback.answer(t["none_user"], show_alert=True)
        return

    bookings = await get_user_bookings(user.id)
    
    if not bookings:
        await callback.answer(t["no_user_bookings"], show_alert=True)
        return

    await state.set_state(CancelRecord.waiting_for_cancel)
    
    await callback.message.edit_text(
        t["cancel_prompt"],
        reply_markup=get_cancel_booking_keyboard(bookings, lang)
    )
    await callback.answer()


@cancel_record_router.callback_query(F.data.startswith("cancel_id_"), CancelRecord.waiting_for_cancel)
async def process_cancellation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает нажатие на кнопку отмены конкретной записи.
    1. Получает данные о брони.
    2. Отменяет её в БД.
    3. Рассылает уведомления всем пользователям.
    """
    lang, t = await get_lang_and_texts(state)
    booking_id = int(callback.data.split("_")[2])
    
    # 1. Сначала получаем информацию о бронировании (чтобы знать дату/время для рассылки)
    # Важно сделать это ДО отмены, если вдруг логика БД фильтрует отмененные
    booking_info = await get_booking_by_id(booking_id)
    
    if not booking_info:
        await callback.answer(t["cancel_error"], show_alert=True)
        # Обновляем список, вдруг она уже удалена
        await start_cancel_process(callback, state)
        return

    # Сохраняем данные для рассылки
    date_str = booking_info.start_time.strftime("%d.%m")
    time_str = f"{booking_info.start_time.strftime('%H:%M')} - {booking_info.end_time.strftime('%H:%M')}"
    machine_num = booking_info.machine.number_machine
    
    # Локализация типа машинки для рассылки (берем из текущего языка админа или дефолт)
    # Для красоты можно использовать общие словари, но здесь возьмем из текущего контекста t
    m_type_key = "machine_type_wash" if booking_info.machine.type_machine == "WASH" else "machine_type_dry"
    machine_type_str = t.get(m_type_key, booking_info.machine.type_machine)

    # 2. Выполняем отмену
    success = await cancel_booking(booking_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅", show_alert=False)
        await callback.message.edit_text(
            t["cancel_confirm_success"],
            reply_markup=get_back_to_sections_keyboard(lang)
        )
        await state.clear()
        
        # 3. ЗАПУСК РАССЫЛКИ (Фоновая задача)
        # Формируем текст уведомления
        notification_text = t["slot_freed_notification"].format(
            date=date_str,
            time=time_str,
            m_type=machine_type_str,
            m_num=machine_num
        )
        
        # Запускаем рассылку без ожидания (чтобы бот не завис)
        asyncio.create_task(broadcast_free_slot(bot, notification_text, exclude_tg_id=callback.from_user.id))
        
    else:
        await callback.answer(t["cancel_error"], show_alert=True)
        await start_cancel_process(callback, state)


async def broadcast_free_slot(bot: Bot, text: str, exclude_tg_id: int):
    """
    Рассылает сообщение всем пользователям из БД.
    Игнорирует ошибки блокировки бота пользователями.
    """
    all_tg_ids = await get_all_users_with_tg()
    
    count = 0
    for tg_id in all_tg_ids:
        if tg_id == exclude_tg_id:
            continue # Не отправляем тому, кто отменил
            
        try:
            await bot.send_message(chat_id=tg_id, text=text)
            count += 1
            # Небольшая задержка, чтобы не словить лимиты телеграма (особенно если пользователей > 30)
            await asyncio.sleep(0.05) 
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            pass
        except TelegramRetryAfter as e:
            # Лимит скорости, ждем
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=tg_id, text=text)
            except:
                pass
        except Exception as e:
            logging.error(f"Broadcast error for {tg_id}: {e}")

    logging.info(f"Broadcast finished. Sent to {count} users.")


@cancel_record_router.callback_query(F.data == "back_to_sections", CancelRecord.waiting_for_cancel)
async def back_from_cancel(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await state.clear()
    await state.update_data(lang=lang)
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )