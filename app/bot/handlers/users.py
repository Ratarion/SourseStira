from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from app.locales import ru, en, cn
from app.bot.states import Auth, AddRecord

#Импорт клавы
from app.bot.keyboards import (
    kb_welcom, 
    get_section_keyboard, 
    get_time_slots_keyboard, 
    get_machines_keyboard,
    get_years_keyboard,   
    get_months_keyboard   
)

#Ипорт запросов
from app.repositories.laundry_repo import (
    get_user_by_tg_id, 
    find_resident_by_fio,     
    find_resident_by_id_card,  
    activate_resident_user,    
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
        await cmd_start_auth(message, state) 


@user_router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    await callback.message.delete()
    await cmd_start_auth(callback.message, state)


# ---------------------------------------------------------
# ЛОГИКА АУТЕНТИФИКАЦИИ (Локализовано)
# ---------------------------------------------------------

async def cmd_start_auth(message: Message, state: FSMContext):
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
        await message.answer(t["auth"])
        await state.set_state(Auth.waiting_for_fio)


@user_router.message(Auth.waiting_for_fio)
async def process_fio_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    text = message.text.strip()
    parts = text.split()

    # Поиск пользователя в базе по ФИО
    resident = await find_resident_by_fio(parts)

    if len(parts) < 2:
        await message.answer(t["write_FIO"])
        return

    if resident:
        # Успех: ФИО найдено. Проверяем, не занят ли аккаунт (опционально)
        if resident.tg_id and resident.tg_id != message.from_user.id:
             # Если у этого ФИО уже есть ДРУГОЙ tg_id
            await message.answer(t["other_tg_id"])
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
        await message.answer(t["seek_cards"])
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
            await message.answer(t["other_tg_id"])
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
        await message.answer(t["none_user"])
        # Можно сбросить или оставить в ожидании ввода
        # await state.clear()
        
# ---------------------------------------------------------
# ЛОГИКА ЗАПИСИ НА СТИРКУ (Локализовано)
# ---------------------------------------------------------

#Запись на стирку
# 1. Начало записи: Выбор года
@user_router.callback_query(F.data == "record")
async def start_record(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    # Генерируем список: текущий год и следующий
    current_year = datetime.now().year
    years_list = [current_year, current_year + 1]

    await state.set_state(AddRecord.waiting_for_year)
    
    # Текст: "Выберите дату" (или добавьте ключ "select_year" в словарь)
    await callback.message.edit_text(
        t["record_start"], 
        reply_markup=get_years_keyboard(years_list, lang) 
    )

# 2. Обработка выбора года -> Выбор месяца
@user_router.callback_query(F.data.startswith("year_"))
async def process_year_selection(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    # Получаем год из callback (например, year_2024)
    selected_year = int(callback.data.split("_")[1])
    
    # Сохраняем год в состояние
    await state.update_data(year=selected_year)
    await state.set_state(AddRecord.waiting_for_month)

    # Показываем клавиатуру месяцев
    # (Предположим, что нужен текст "Выберите месяц". Если его нет, используем record_start)
    await callback.message.edit_text(
        f"{t['record_start']} (Month)", # Лучше добавить ключ "choose_month" в словари
        reply_markup=get_months_keyboard(selected_year, lang)
    )

# 3. Обработка выбора месяца -> Выбор дня (Календарь)
@user_router.callback_query(F.data.startswith("month_"))
async def process_month_selection(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    
    # callback: month_2024_5
    parts = callback.data.split("_")
    year = int(parts[1])
    month = int(parts[2])

    await state.update_data(month=month)
    await state.set_state(AddRecord.waiting_for_day)
    

    await callback.message.edit_text(
        f"Выбран {month}.{year}. Теперь выберите день (Функционал календаря дней).",
        
        SimpleCalendar().start_calendar()
    )

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