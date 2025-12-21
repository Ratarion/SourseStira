from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_section_keyboard
from app.bot.states import DisplayRecords
from app.repositories.laundry_repo import get_user_by_tg_id, get_user_bookings, cancel_booking
import logging

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
    
    if not bookings:
        no_bookings_text = t.get("no_user_bookings", "У вас нет записей.")
        await callback.message.edit_text(no_bookings_text, reply_markup=get_section_keyboard(lang))
        await state.clear()
        logging.info(f"No bookings for user {user.id}")
        return

    lines = []
    
    for b in bookings[:20]:
        start_str = b.start_time.strftime("%d.%m.%Y %H:%M") if b.start_time else "—"
        machine_num = b.machine.number_machine if hasattr(b, 'machine') and b.machine else "—"
        machine_type = b.machine.type_machine if hasattr(b, 'machine') and b.machine else "—"
        machine_label = t.get('machine', 'Машина')
        lines.append(f"#{b.id} • {start_str} • {machine_label} №{machine_num} ({machine_type})")

    title = t.get("show_records_title", "Ваши записи:")
    text = title + "\n\n" + "\n".join(lines)

    try:
        await callback.message.edit_text(text, reply_markup=get_section_keyboard(lang))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer() # Просто убираем анимацию загрузки с кнопки
        else:
            raise e

    await callback.answer()
    logging.info(f"Displayed {len(bookings)} bookings for user {user.id}")
