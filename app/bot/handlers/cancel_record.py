# app/bot/handlers/cancel_record.py
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
    Обрабатывает отмену и запускает мульти-язычную рассылку.
    """
    lang, t = await get_lang_and_texts(state)
    booking_id = int(callback.data.split("_")[2])
    
    booking_info = await get_booking_by_id(booking_id)
    
    if not booking_info:
        await callback.answer(t["cancel_error"], show_alert=True)
        await start_cancel_process(callback, state)
        return

    # Сохраняем "сырые" данные для рассылки (не переведенные)
    broadcast_data = {
        "date_str": booking_info.start_time.strftime("%d.%m"),
        "time_str": f"{booking_info.start_time.strftime('%H:%M')} - {booking_info.end_time.strftime('%H:%M')}",
        "machine_num": booking_info.machine.number_machine,
        "raw_machine_type": booking_info.machine.type_machine # "WASH" или "DRY"
    }

    success = await cancel_booking(booking_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅", show_alert=False)
        await callback.message.edit_text(
            t["cancel_confirm_success"],
            reply_markup=get_back_to_sections_keyboard(lang)
        )
        await state.clear()
        
        # ЗАПУСК РАССЫЛКИ
        # Передаем не текст, а данные (broadcast_data)
        asyncio.create_task(broadcast_free_slot(bot, broadcast_data, exclude_tg_id=callback.from_user.id))
        
    else:
        await callback.answer(t["cancel_error"], show_alert=True)
        await start_cancel_process(callback, state)


async def broadcast_free_slot(bot: Bot, data: dict, exclude_tg_id: int):
    """
    Рассылает сообщение, подбирая язык для каждого пользователя.
    """
    # Получаем список (tg_id, lang_code)
    users_data = await get_all_users_with_tg()
    
    count = 0
    for tg_id, user_lang in users_data:
        if tg_id == exclude_tg_id:
            continue
            
        # 1. Определяем словарь текстов для конкретного пользователя
        # Если языка нет в словаре, берем RU по умолчанию
        target_t = ALL_TEXTS.get(user_lang, ALL_TEXTS['RU'])
        
        # 2. Переводим тип машины (Washing/Drying) на язык получателя
        if data["raw_machine_type"] == "WASH":
            m_type_str = target_t.get("machine_type_wash", "Стирка")
        else:
            m_type_str = target_t.get("machine_type_dry", "Сушка")

        # 3. Формируем текст на нужном языке
        try:
            notification_text = target_t["slot_freed_notification"].format(
                date=data["date_str"],
                time=data["time_str"],
                m_type=m_type_str,
                m_num=data["machine_num"]
            )
            
            await bot.send_message(chat_id=tg_id, text=notification_text)
            count += 1
            await asyncio.sleep(0.05) 

        except TelegramForbiddenError:
            pass # Бот заблокирован
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=tg_id, text=notification_text)
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