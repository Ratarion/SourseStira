import asyncio
import logging
from aiogram import Router, F, Bot
from app.bot.utils.translate import ALL_TEXTS
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
from app.bot.utils.broadcaster import broadcast_slot_freed

cancel_record_router = Router()

@cancel_record_router.callback_query(F.data == "remove_records")
async def start_cancel_process(callback: CallbackQuery, state: FSMContext):
    # (Этот код остается без изменений - показ списка записей)
    lang, t = await get_lang_and_texts(state)
    user = await get_user_by_tg_id(callback.from_user.id)
    
    if not user:
        await callback.answer(t["none_user"], show_alert=True)
        return

    bookings = await get_user_bookings(user.id)
    if not bookings:
        await callback.answer(t["no_user_bookings"], show_alert=True)
        return

    await callback.message.edit_text(
        t["cancel_prompt"], 
        reply_markup=get_cancel_booking_keyboard(bookings, lang)
    )
    await state.set_state(CancelRecord.waiting_for_cancel)
    await callback.answer()


@cancel_record_router.callback_query(F.data.startswith("cancel_"), CancelRecord.waiting_for_cancel)
async def process_cancel_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    booking_id = int(callback.data.split("_")[-1])
    lang, t = await get_lang_and_texts(state)
    
    # 1. Сначала получаем данные о бронировании, пока не удалили
    booking = await get_booking_by_id(booking_id)
    
    if not booking:
        await callback.answer(t["cancel_error"], show_alert=True)
        # Обновляем список, так как эта запись исчезла
        await start_cancel_process(callback, state)
        return
    

    # Сохраняем данные для рассылки
    booking_data = {
        "date_str": booking.start_time.strftime("%d.%m"),
        "start_time_str": booking.start_time.strftime("%H:%M"),
        "end_time_str": booking.end_time.strftime("%H:%M"),
        "machine_type": booking.machine.type_machine, 
        "machine_num": booking.machine.number_machine
    }

    # 2. Удаляем запись
    success = await cancel_booking(booking_id)
    
    if success:
        await callback.answer(t["cancel_confirm_success"], show_alert=True)
        
        # Возвращаем пользователя в меню или список
        await callback.message.edit_text(
            t["cancel_confirm_success"],
            reply_markup=get_back_to_sections_keyboard(lang)
        )
        await state.clear()

        # 3. ЗАПУСКАЕМ РАССЫЛКУ (В ФОНЕ)
        # Передаем bot, данные и ID того, кто отменил (чтобы ему не слать уведомление)
        asyncio.create_task(
            broadcast_slot_freed(bot, booking_data, exclude_tg_id=callback.from_user.id)
        )
        
    else:
        await callback.answer(t["cancel_error"], show_alert=True)


@cancel_record_router.callback_query(F.data == "back_to_sections", CancelRecord.waiting_for_cancel)
async def back_from_cancel(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await state.clear()
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )