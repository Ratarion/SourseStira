from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from app.locales import ru, en, cn
# Обратите внимание на импорт нового состояния Auth
from app.bot.states import Auth, AddRecord 
from app.bot.keyboards import (
    kb_welcom, 
    get_section_keyboard, 
    get_time_slots_keyboard, 
    get_machines_keyboard
)

# Импортируем новые функции репозитория
from app.repositories.laundry_repo import (
    get_user_by_tg_id, 
    find_resident_by_fio,      # НОВАЯ
    find_resident_by_id_card,  # НОВАЯ
    activate_resident_user,    # НОВАЯ
    get_available_slots, 
    get_all_machines, 
    is_slot_free, 
    create_booking
)

user_router = Router()

ALL_TEXTS = {**ru.RUtexts, **en.ENtexts, **cn.CNtexts}

async def get_lang_and_texts(state: FSMContext) -> tuple[str, dict]:
    data = await state.get_data()
    lang = data.get('lang', 'RU')
    return lang, ALL_TEXTS.get(lang, ALL_TEXTS['RU'])


# ---------------------------------------------------------
# ЛОГИКА ВЫБОРА ЯЗЫКА
# ---------------------------------------------------------

@user_router.message(CommandStart())
async def cmd_start_initial(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'lang' not in data:
        # Используем текст из ALL_TEXTS
        await message.answer(
            ALL_TEXTS["RU"]["welcome_lang_choice"], 
            reply_markup=kb_welcom
        )
    else:
        await cmd_start_registered(message, state) 


@user_router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    await callback.message.delete()
    await cmd_start_registered(callback.message, state)


# ---------------------------------------------------------
# ЛОГИКА РЕГИСТРАЦИИ (Локализовано)
# ---------------------------------------------------------

# ---------------------------------------------------------
# ЛОГИКА АУТЕНТИФИКАЦИИ (БЕЗ РЕГИСТРАЦИИ НОВОГО)
# ---------------------------------------------------------

async def cmd_start_registered(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    
    # 1. Проверяем, привязан ли уже этот ТГ к кому-то
    existing_user = await get_user_by_tg_id(tg_id)
    
    lang, t = await get_lang_and_texts(state)

    if existing_user:
        # Если пользователь уже активирован -> Главное меню
        await message.answer(
            f"{t['hello_user'].replace('{name}', existing_user.first_name)}", 
            reply_markup=get_section_keyboard(lang)
        )
    else:
        # Если нет -> Просим ввести ФИО для поиска в базе
        # Текст: "Введите ваше ФИО (Иванов Иван Иванович) для входа"
        # (Вам возможно придется добавить ключи в словари локализации, если их нет)
        welcome_text = t.get("auth_enter_fio", "Введите ФИО (Фамилия Имя Отчество) для авторизации:") 
        await message.answer(welcome_text)
        await state.set_state(Auth.waiting_for_fio)


@user_router.message(Auth.waiting_for_fio)
async def process_fio_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    text = message.text.strip()
    parts = text.split()
    
    # Простая валидация на 3 слова
    if len(parts) < 3:
        await message.answer(t["reg_fio_error"]) # "Введите полное ФИО..."
        return

    # Поиск пользователя в базе по ФИО
    resident = await find_resident_by_fio(parts)

    if resident:
        # Успех: ФИО найдено. Проверяем, не занят ли аккаунт (опционально)
        if resident.tg_id and resident.tg_id != message.from_user.id:
             # Если у этого ФИО уже есть ДРУГОЙ tg_id
            await message.answer("Этот пользователь уже зарегистрирован с другого аккаунта Telegram.")
            return

        # Привязываем текущий Telegram ID к найденному резиденту
        await activate_resident_user(resident.id, message.from_user.id)
        
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}", 
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    
    else:
        # Провал: ФИО не найдено. Просим ввести номер зачетки.
        # Текст: "ФИО не найдено. Пожалуйста, введите номер зачетки/студенческого:"
        error_text = t.get("auth_fio_fail", "Пользователь с таким ФИО не найден. Введите номер вашей зачетной книжки (только цифры):")
        await message.answer(error_text)
        await state.set_state(Auth.waiting_for_id_card)


@user_router.message(Auth.waiting_for_id_card)
async def process_id_card_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    if not message.text.isdigit():
        await message.answer(t["reg_id_error"]) # "Только цифры..."
        return

    id_card_num = int(message.text)
    
    # Поиск по зачетке
    resident = await find_resident_by_id_card(id_card_num)

    if resident:
         # Успех
        if resident.tg_id and resident.tg_id != message.from_user.id:
            await message.answer("Этот пользователь уже зарегистрирован с другого аккаунта.")
            return

        await activate_resident_user(resident.id, message.from_user.id)
        
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}", 
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    else:
        # Провал окончательный
        # Текст: "Пользователь не найден. Обратитесь к администратору."
        fail_text = t.get("auth_fail_final", "Данные не найдены в системе. Обратитесь к администратору.")
        await message.answer(fail_text)
        # Можно сбросить или оставить в ожидании ввода
        # await state.clear()
        
# ---------------------------------------------------------
# ЛОГИКА ЗАПИСИ НА СТИРКУ (Локализовано)
# ---------------------------------------------------------

@user_router.callback_query(F.data == "record")
async def start_record(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    # Локализовано
    await callback.message.answer(t["record_start"]) 
    # await state.set_state(AddRecord.waiting_for_year)

# Ваш код выбора дня
@user_router.callback_query(F.data.startswith("day_"))
async def process_day(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    _, year, month, day = callback.data.split("_")
    date = datetime(int(year), int(month), int(day))

    await state.update_data(chosen_date=date.date())

    slots = await get_available_slots(date)
    if not slots:
        # Локализовано
        await callback.message.edit_text(
            t["slots_none"].replace("{date}", date.strftime('%d.%m.%Y')),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t["back"], callback_data="back_to_month")]
            ])
        )
        return

    # Локализовано
    await callback.message.edit_text(
        t["time_prompt"].replace("{date}", date.strftime('%d.%m.%Y')),
        reply_markup=get_time_slots_keyboard(date, slots, lang)
    )
    await state.set_state(AddRecord.waiting_for_time)

# Ваш код выбора времени
@user_router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    _, y, m, d, h = callback.data.split("_")
    chosen_dt = datetime(int(y), int(m), int(d), int(h))

    await state.update_data(start_time=chosen_dt)

    machines = await get_all_machines()
    available_machines = []
    for machine in machines:
        if await is_slot_free(machine.id, chosen_dt):
            available_machines.append(machine)

    if not available_machines:
        # Локализовано
        await callback.message.edit_text(t["machines_none"])
        return

    # Локализовано
    await callback.message.edit_text(
        t["machine_prompt"].replace("{datetime}", chosen_dt.strftime('%d.%m %H:%M')),
        reply_markup=get_machines_keyboard(available_machines, lang)
    )

# Ваш код создания брони
@user_router.callback_query(F.data.startswith("machine_"))
async def process_machine(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    machine_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    start_time = data["start_time"]
    end_time = start_time + timedelta(hours=2) # Предполагаем 2 часа стирки
    
    user = await get_user_by_tg_id(callback.from_user.id)

    try:
        booking = await create_booking(
            user_id=user.id,
            machine_id=machine_id,
            start_time=start_time
        )
        # Локализовано
        await callback.message.edit_text(
            t["booking_success"].format(
                machine_num=booking.machine.number_machine,
                start=start_time.strftime('%d.%m.%Y %H:%M'),
                end=end_time.strftime('%H:%M')
            ),
            reply_markup=get_section_keyboard(lang)
        )
    except ValueError:
        # Локализовано
        await callback.message.edit_text(t["booking_error"])
    
    await state.clear()
    await state.update_data(lang=lang)