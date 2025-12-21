# app/bot/handlers/report.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.bot.utils.translate import get_lang_and_texts
# Импортируем клавиатуру с кнопкой "Назад"
from app.bot.keyboards import get_section_keyboard, get_back_to_sections_keyboard
from app.bot.states import Report
from app.repositories.laundry_repo import get_user_by_tg_id, create_notification

report_router = Router()

@report_router.callback_query(F.data == "report")
async def report_problem(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    # Добавляем кнопку "Назад" к сообщению с просьбой описать проблему
    await callback.message.edit_text(
        t.get("report_prompt", "Укажите номер и тип машинки и опишите проблему:"), 
        reply_markup=get_back_to_sections_keyboard(lang)
    )
    await state.set_state(Report.waiting_for_report)
    await callback.answer()

@report_router.message(Report.waiting_for_report)
async def process_report(message: Message, state: FSMContext, bot: Bot):
    lang, t = await get_lang_and_texts(state)

    user = await get_user_by_tg_id(message.from_user.id)
 
    if not user:
        await message.answer(
            t.get("none_user", "Пользователь не найден."), 
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        return
    
    await create_notification(resident_id=user.id, description=message.text)
    
    # ИЗМЕНЕНИЕ: Отправляем подтверждение с кнопкой "Назад" вместо главного меню
    await message.answer(
        t.get("report_sent", "Сообщение отправлено."), 
        reply_markup=get_back_to_sections_keyboard(lang)
    )
    # Важно: мы НЕ делаем state.clear() здесь, чтобы бот ждал нажатия кнопки "Назад" 
    # (или следующего сообщения, если пользователь решит отправить еще один репорт).

# Обработка нажатия "Назад" из состояния Report
@report_router.callback_query(F.data == "back_to_sections", Report.waiting_for_report)
async def back_from_report(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    # Сбрасываем состояние и восстанавливаем язык
    await state.clear()
    await state.update_data(lang=lang)

    # Возвращаем пользователя в главное меню
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await callback.answer()