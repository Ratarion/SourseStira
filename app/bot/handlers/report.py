from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_section_keyboard
from app.bot.states import Report
from app.config import ADMIN_ID  # Добавь в config.py: ADMIN_ID = your_id

report_router = Router()

@report_router.callback_query(F.data == "report_in_admin")
async def report_problem(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(t.get("report_prompt", "Опишите проблему:"), reply_markup=None)
    await state.set_state(Report.waiting_for_report)
    await callback.answer()

@report_router.message(state=Report.waiting_for_report)
async def process_report(message: Message, state: FSMContext, bot: Bot):  # Добавь bot если нужно
    lang, t = await get_lang_and_texts(state)
    await bot.send_message(ADMIN_ID, f"Report from {message.from_user.id}: {message.text}")
    await message.answer(t.get("report_sent", "Сообщение отправлено."), reply_markup=get_section_keyboard(lang))
    await state.clear()