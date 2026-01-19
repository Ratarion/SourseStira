from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import kb_welcom, get_section_keyboard
from app.repositories.laundry_repo import (
    get_user_by_tg_id,
    find_resident_by_fio,
    find_resident_by_id_card,
    activate_resident_user,
    update_user_language 
)
from app.bot.states import Auth
from app.bot.utils.translate import get_lang_and_texts, ALL_TEXTS

auth_router = Router()

@auth_router.message(CommandStart())
async def cmd_start_initial(message: Message, state: FSMContext):
    data = await state.get_data()
    # Если язык еще не выбран, предлагаем выбрать
    if 'lang' not in data:
        await message.answer(
            ALL_TEXTS["RU"]["welcome_lang_choice"],
            reply_markup=kb_welcom
        )
    else:
        await cmd_start_auth(message, state)

@auth_router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    # 1. Получаем выбранный язык
    lang = callback.data.split("_")[1]
    
    # 2. Обновляем состояние
    await state.update_data(lang=lang)
    
    # 3. Получаем тексты для выбранного языка
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    
    # 4. Проверяем, кто нажал кнопку (пользователь)
    tg_id = callback.from_user.id
    user = await get_user_by_tg_id(tg_id)

    # Удаляем сообщение с выбором языка, чтобы не засорять чат
    await callback.message.delete()

    if user:
        # --- ЕСЛИ ПОЛЬЗОВАТЕЛЬ УЖЕ ЕСТЬ В БАЗЕ ---
        # Обновляем язык в базе данных
        await update_user_language(tg_id, lang)
        
        # Отправляем главное меню на новом языке
        # Используем .replace, как у вас принято в проекте, или .format
        await callback.message.answer(
            t['hello_user'].replace('{name}', user.first_name),
            reply_markup=get_section_keyboard(lang)
        )
    else:
        # --- ЕСЛИ ЭТО НОВЫЙ ПОЛЬЗОВАТЕЛЬ (регистрация) ---
        # Запускаем процедуру авторизации
        await callback.message.answer(t["auth"])
        await state.set_state(Auth.waiting_for_fio)
    
    await callback.answer()

async def cmd_start_auth(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    existing_user = await get_user_by_tg_id(tg_id)
    lang, t = await get_lang_and_texts(state)

    if existing_user:
        # Если пользователь уже есть, но в State выбран другой язык, можно обновить его в базе
        # (Это опционально, но удобно: если юзер нажал /start и выбрал язык заново)
        if existing_user.language != lang:
             await update_user_language(tg_id, lang)
        
        await message.answer(
            t['hello_user'].format(name=existing_user.first_name),
            reply_markup=get_section_keyboard(lang)
        )
    else:
        await message.answer(t["auth"])
        await state.set_state(Auth.waiting_for_fio)

@auth_router.message(Auth.waiting_for_fio)
async def process_fio_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state) # Получаем язык из FSM
    text = message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer(t["write_FIO"])
        return
    
    resident = await find_resident_by_fio(parts)
    if resident:
        if resident.tg_id and resident.tg_id != message.from_user.id:
            await message.answer(t["other_tg_id"])
            return
            
        # ✅ ПЕРЕДАЕМ ЯЗЫК В БАЗУ
        await activate_resident_user(resident.id, message.from_user.id, language=lang)
        
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}",
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        # Важно оставить язык в state, чтобы сессия продолжилась на нужном языке
        await state.update_data(lang=lang) 
    else:
        await message.answer(t["seek_cards"])
        await state.set_state(Auth.waiting_for_id_card)

@auth_router.message(Auth.waiting_for_id_card)
async def process_id_card_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    if not message.text.isdigit():
        await message.answer(t["reg_id_error"])
        return
        
    id_card_num = int(message.text)
    resident = await find_resident_by_id_card(id_card_num)
    
    if resident:
        if resident.tg_id and resident.tg_id != message.from_user.id:
            await message.answer(t["other_tg_id"])
            return
            
        # ✅ ПЕРЕДАЕМ ЯЗЫК В БАЗУ
        await activate_resident_user(resident.id, message.from_user.id, language=lang)
        
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}",
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    else:
        await message.answer(t["none_user"])


@auth_router.callback_query(F.data == "change_language")
async def process_change_language_btn(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Сменить язык' из главного меню.
    Показывает клавиатуру выбора языка.
    """
    # Берем тексты для текущего языка, чтобы заголовок был понятен
    lang, t = await get_lang_and_texts(state)
    
    # Показываем сообщение с выбором языка (текст welcome_lang_choice у вас мульти-язычный сразу)
    await callback.message.edit_text(
        ALL_TEXTS["RU"]["welcome_lang_choice"], 
        reply_markup=kb_welcom
    )
    await callback.answer()