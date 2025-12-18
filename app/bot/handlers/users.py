from aiogram import Router, F
import asyncio
from aiogram.filters import CommandStart
from app.bot.calendar_utils import CustomLaundryCalendar
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, date, timedelta
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
try:
    from aiogram_calendar.schemas import SimpleCalendarAction
except ImportError:
    class SimpleCalendarAction:
        DAY = "DAY"


from app.bot.calendar_utils import CustomLaundryCalendar

from app.locales import ru, en, cn
from app.bot.states import Auth, AddRecord

#Импорт клавы
from app.bot.keyboards import (
    kb_welcom,
    get_section_keyboard,
    get_time_slots_keyboard,
    get_machines_keyboard,
    get_exit_keyboard,
    get_machine_type_keyboard
)

#Ипорт запросов
from app.repositories.laundry_repo import (
    get_user_by_tg_id,
    get_user_bookings,
    find_resident_by_fio,
    find_resident_by_id_card,
    activate_resident_user,
    get_available_slots,
    get_available_machines,
    get_all_machines,
    is_slot_free,
    create_booking,
    get_month_workload,
    get_total_daily_capacity_by_type
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
# ЛОГИКА ЗАПИСИ НА СТИРКУ (ОБНОВЛЕННАЯ)
# ---------------------------------------------------------

# Вспомогательная функция для генерации календаря с данными
async def get_colored_calendar(year: int, month: int, locale: str):
    workload = await get_month_workload(year, month)
    max_slots = await get_total_daily_capacity_by_type()

    calendar = CustomLaundryCalendar(
        workload=workload,
        max_capacity=max_slots,
        locale=locale
    )
    return await calendar.start_calendar(year=year, month=month)


# 1. Начало записи
@user_router.callback_query(F.data == "record")
async def process_record_start(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)

    # Проверка работоспособности машин перед выбором типа
    max_capacity = await get_total_daily_capacity_by_type()  # Исправлено: используем функцию без типа, но ниже адаптируем для типа
    if max_capacity == 0:
        await callback.answer(t["no_active_machines"], show_alert=True)
        await callback.message.edit_text(t["section_menu_title"], reply_markup=get_section_keyboard(lang))
        await state.clear()
        return

    await state.update_data(max_capacity=max_capacity)

    await callback.message.edit_text(
        t["select_machine_type"],
        reply_markup=get_machine_type_keyboard(lang)
    )
    await state.set_state(AddRecord.waiting_for_machine_type)
    await callback.answer()


@user_router.callback_query(F.data.startswith("type_"), AddRecord.waiting_for_machine_type)
async def process_machine_type(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    machine_type_code = callback.data.split("_")[1]

    # Определяем тип для БД
    type_map = {
        'WASH': t["machine_type_wash"],
        'DRY':  t["machine_type_dry"]
    }
    machine_type_db = type_map.get(machine_type_code, 'Стирка')

    # Проверка работоспособности для выбранного типа
    max_capacity = await get_total_daily_capacity_by_type(machine_type_db)
    if max_capacity == 0:
        await callback.answer(t["no_active_machines_type"], show_alert=True)
        await callback.message.edit_text(
            t["select_machine_type"],
            reply_markup=get_machine_type_keyboard(lang)
        )
        return

    await state.update_data(
        machine_type=machine_type_db,
        max_capacity=max_capacity
    )
    # Получаем загруженность месяца и max capacity для индикаторов в календаре
    today = datetime.now()
    workload = await get_month_workload(today.year, today.month, machine_type_db)
    max_capacity = await get_total_daily_capacity_by_type(machine_type_db)

    now = datetime.now()
    year = now.year
    month = now.month

    workload = await get_month_workload(year, month, machine_type_db)

    # Создаём кастомный календарь с индикаторами (🟢/🟡/🔴)
    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_capacity, locale=lang.lower() if lang in ['ru', 'en', 'cn'] else 'ru')

    await callback.message.edit_text(
        t["record_start"],
        reply_markup=await calendar.start_calendar(now.year, now.month),
        parse_mode="HTML"
    )

    await state.set_state(AddRecord.waiting_for_day)
    await callback.answer()

# 2. ЕДИНЫЙ Хендлер для календаря (и выбор дня, и навигация)
@user_router.callback_query(CustomLaundryCalendar.calendar_callback.filter(), AddRecord.waiting_for_day)
async def process_simple_calendar(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    max_capacity = data.get('max_capacity', 0)
    machine_type_db = data['machine_type']

    if callback_data.act in ['PREV-MONTH', 'NEXT-MONTH']:
        await callback.answer(t["navigation_disabled"], show_alert=True)  # Или просто await callback.answer()
        return

    workload = await get_month_workload(callback_data.year, callback_data.month, machine_type_db)

    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_capacity, locale=lang.lower())

    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        if callback_data.action == SimpleCalendarAction.DAY:
            if date.date() < datetime.now().date():
                await callback.answer(t["past_date_error"], show_alert=True)
                return

            day = date.day
            used = workload.get(day, 0)
            free = max_capacity - used if max_capacity > 0 else 0

            if free <= 0:
                await callback.answer(t["day_fully_booked"], show_alert=True)
                await callback.message.edit_text(
                    t["select_date_prompt"],
                    reply_markup=await calendar.start_calendar(callback_data.year, callback_data.month)
                )
                return

            await state.update_data(chosen_date=date)

            # Адаптируем get_available_slots для типа машины (нужно реализовать в laundry_repo)
            slots = await get_available_slots(date, machine_type=machine_type_db)

            if not slots:
                await callback.answer(t["no_slots_available"], show_alert=True)
                await callback.message.edit_text(
                    t["select_date_prompt"],
                    reply_markup=await calendar.start_calendar(callback_data.year, callback_data.month)
                )
                return

            await callback.message.edit_text(
                t["select_time_prompt"].replace("{date}", date.strftime("%d.%m")),
                reply_markup=get_time_slots_keyboard(date, slots, lang)
            )
            await state.set_state(AddRecord.waiting_for_time)
            await callback.answer()
            return

        await callback.answer()
    else:
        await callback.answer()

# Код выбора времени
@user_router.callback_query(F.data.startswith("time_"), AddRecord.waiting_for_time)
async def process_time_slot(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()

    parts = callback.data.split("_")
    year, month, day, hour, minute = map(int, parts[1:])
    chosen_dt = datetime(year, month, day, hour, minute)

    await state.update_data(start_time=chosen_dt)

    machine_type_db = data['machine_type']
    available_machines = await get_available_machines(chosen_dt, machine_type_db)

    if not available_machines:
        await callback.answer(t["no_available_slots_alert"], show_alert=True)
        await callback.message.edit_text(t["machines_none"])
        return

    await callback.message.edit_text(
        t["machine_prompt"].replace("{datetime}", chosen_dt.strftime('%d.%m %H:%M')),
        reply_markup=get_machines_keyboard(available_machines, lang)
    )
    await state.set_state(AddRecord.waiting_for_machine)
    await callback.answer()

# Код создания брони
@user_router.callback_query(F.data.startswith("machine_"), AddRecord.waiting_for_machine)
async def process_machine(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    machine_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    duration_minutes = 90
    start_time = data["start_time"]
    end_time = start_time + timedelta(minutes=duration_minutes)

    user = await get_user_by_tg_id(callback.from_user.id)

    try:
        if await is_slot_free(machine_id, start_time):
            result = await create_booking(
                user_id=user.id,
                machine_id=machine_id,
                start_time=start_time
            )

            await callback.message.edit_text(
                t["booking_success"].format(
                    machine_num=result['machine'].number_machine,
                    start=start_time.strftime('%d.%m.%Y %H:%M'),
                    end=end_time.strftime('%H:%M')
                ),
                reply_markup=get_exit_keyboard(lang)
            )
            await state.clear()
        else:
            await callback.answer(t["slot_just_taken"], show_alert=True)

    except Exception as e:
        await callback.message.edit_text(t["booking_error"])

    await state.clear()
    await state.update_data(lang=lang)

@user_router.callback_query(F.data == "back_to_sections", AddRecord.waiting_for_machine_type)
async def process_back_to_sections(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await state.clear()
    await callback.answer()

@user_router.callback_query(F.data == "back_to_calendar", AddRecord.waiting_for_time)
async def process_back_to_calendar(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    machine_type_db = data['machine_type']
    max_capacity = data.get('max_capacity', 0)
    now = datetime.now()
    workload = await get_month_workload(now.year, now.month, machine_type_db)
    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_capacity, locale=lang.lower())
    await callback.message.edit_text(
        t["record_start"],
        reply_markup=await calendar.start_calendar(now.year, now.month)
    )
    await state.set_state(AddRecord.waiting_for_day)
    await callback.answer()

@user_router.callback_query(F.data == "back_to_time", AddRecord.waiting_for_machine)
async def process_back_to_time(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    chosen_date = data['chosen_date']
    machine_type_db = data['machine_type']
    slots = await get_available_slots(chosen_date, machine_type=machine_type_db)
    await callback.message.edit_text(
        t["select_time_prompt"].replace("{date}", chosen_date.strftime("%d.%m")),
        reply_markup=get_time_slots_keyboard(chosen_date, slots, lang)
    )
    await state.set_state(AddRecord.waiting_for_time)
    await callback.answer()

@user_router.callback_query(F.data == "exit")
async def process_exit(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await state.clear()
    await callback.answer()
