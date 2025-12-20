from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_section_keyboard, InlineKeyboardButton, InlineKeyboardMarkup
from app.bot.states import CancelRecord
from app.bot.states import DisplayRecords
from app.repositories.laundry_repo import get_user_by_tg_id, get_user_bookings, cancel_booking
import logging

records_router = Router()

@records_router.callback_query(F.data == "cancel_record")
async def cancel_record(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await state.set_state(CancelRecord.waiting_for_cancel)
    user = await get_user_by_tg_id(callback.from_user.id)
    bookings = await get_user_bookings(user.id)
    if not bookings:
        await callback.message.edit_text(t["no_user_bookings"], reply_markup=get_section_keyboard(lang))
        return
    buttons = []
    for b in bookings:
        text = f"#{b.id} {b.start_time.strftime('%d.%m %H:%M')}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"cancel_{b.id}")])
    buttons.append([InlineKeyboardButton(text=t["back"], callback_data="back_to_sections")])
    await callback.message.edit_text(t.get("cancel_booking_title", "Выберите запись для отмены:"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


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
    await callback.message.edit_text(text, reply_markup=get_section_keyboard(lang))
    await callback.answer()
    logging.info(f"Displayed {len(bookings)} bookings for user {user.id}")


@records_router.callback_query(F.data.startswith("cancel_"))
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    booking_id = int(callback.data.split("_")[1])
    await cancel_booking(booking_id)
    await callback.message.edit_text(t.get("booking_cancelled", "Запись отменена."), reply_markup=get_section_keyboard(lang))
    await state.clear()
    await callback.answer()