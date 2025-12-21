from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
from app.bot.keyboards import get_section_keyboard
from app.bot.states import Report
from app.repositories.laundry_repo import get_user_by_tg_id, create_notification

report_router = Router()

@report_router.callback_query(F.data == "report")
async def report_problem(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(t.get("report_prompt", "Укажите номер и тип машинки и опишите проблему:"), reply_markup=None)
    await state.set_state(Report.waiting_for_report)
    await callback.answer()

@report_router.message(Report.waiting_for_report)
async def process_report(message: Message, state: FSMContext, bot: Bot):
    lang, t = await get_lang_and_texts(state)

    user = await get_user_by_tg_id(message.from_user.id) # 1. Получаем пользователя из БД
 
    if not user:
        await message.answer(t.get("none_user", "Пользователь не найден."), reply_markup=get_section_keyboard(lang))
        await state.clear()
        return
    
    # 2. Записываем в БД
    await create_notification(resident_id=user.id, description=message.text)
    
    await message.answer(t.get("report_sent", "Сообщение отправлено."), reply_markup=get_section_keyboard(lang))
    await state.clear()