from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_section_keyboard
from app.bot.states import DisplayRecords
from app.repositories.laundry_repo import get_user_by_tg_id, get_user_bookings, cancel_booking
import logging
from app.bot.keyboards import get_back_to_sections_keyboard

records_router = Router()


@records_router.callback_query(F.data == "show_records")
async def show_records(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await state.set_state(DisplayRecords.waiting_for_display)
    user = await get_user_by_tg_id(callback.from_user.id)
    
    if not user:
        await callback.answer(t["none_user"], show_alert=True)
        return

    bookings = await get_user_bookings(user.id)
    
    # Кнопка "Назад", которую мы будем везде подставлять вместо меню
    back_kb = get_back_to_sections_keyboard(lang)

    if not bookings:
        no_bookings_text = t.get("no_user_bookings", "У вас нет записей.")
        await callback.message.edit_text(no_bookings_text, reply_markup=back_kb)
        return

    lines = []
    # Напоминаю: здесь мы уже убрали ID по твоей просьбе ранее
    for b in bookings[:20]:
        start_str = b.start_time.strftime("%d.%m.%Y %H:%M") if b.start_time else "—"
        machine_num = b.machine.number_machine if hasattr(b, 'machine') and b.machine else "—"
        machine_type = b.machine.type_machine if hasattr(b, 'machine') and b.machine else "—"
        machine_label = t.get('machine', 'Машина')
        lines.append(f"• {start_str} • {machine_label} №{machine_num} ({machine_type})")

    title = t.get("show_records_title", "Ваши записи:")
    text = title + "\n\n" + "\n".join(lines)

    try:
        # Используем back_kb вместо главного меню
        await callback.message.edit_text(text, reply_markup=back_kb)
    except TelegramBadRequest:
        pass


@records_router.callback_query(F.data == "back_to_sections")
async def back_from_records(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    # Очищаем состояние (выходим из DisplayRecords)
    await state.clear()
    # Восстанавливаем выбранный язык
    await state.update_data(lang=lang)

    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await callback.answer()
