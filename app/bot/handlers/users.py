from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from app.locales import ru, en, cn

from app.bot.states import Registration, AddRecord
from app.bot.keyboards import (
    kb_welcom, 
    get_section_keyboard, 
    get_time_slots_keyboard, 
    get_machines_keyboard
)

from app.repositories.laundry_repo import (
    get_user_by_tg_id, 
    create_new_user,
    get_available_slots, 
    get_all_machines, 
    is_slot_free, 
    create_booking
)

user_router = Router()

# Объединяем словари локализации в один объект
ALL_TEXTS = {**ru.RUtexts, **en.ENtexts, **cn.CNtexts}


# --- Вспомогательная функция для получения языка и текстов ---
async def get_lang_and_texts(state: FSMContext) -> tuple[str, dict]:
    """Получает текущий язык и словарь текстов. По умолчанию RU."""
    data = await state.get_data()
    lang = data.get('lang', 'RU')
    # Используем ALL_TEXTS
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

async def cmd_start_registered(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    existing_user = await get_user_by_tg_id(tg_id)
    
    lang, t = await get_lang_and_texts(state)

    if existing_user:
        await message.answer(
            f"{t['hello_user'].replace('{name}', existing_user.first_name)}", 
            reply_markup=get_section_keyboard(lang)
        )
    else:
        # Локализованный текст reg_start
        await message.answer(t["reg_start"])
        await state.set_state(Registration.waiting_for_fio)


@user_router.message(Registration.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) < 3:
        # Локализовано
        await message.answer(t["reg_fio_error"])
        return

    await state.update_data(fio=parts)
    # Локализовано
    await message.answer(t["reg_room_prompt"])
    await state.set_state(Registration.waiting_for_room)

@user_router.message(Registration.waiting_for_room)
async def process_room(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    if not message.text.isdigit():
        # Локализовано
        await message.answer(t["reg_room_error"])
        return

    await state.update_data(room=int(message.text))
    # Локализовано
    await message.answer(t["reg_id_prompt"])
    await state.set_state(Registration.waiting_for_id_card)

@user_router.message(Registration.waiting_for_id_card)
async def process_id_card(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    if not message.text.isdigit():
        # Локализовано
        await message.answer(t["reg_id_error"])
        return

    data = await state.get_data()
    tg_id = message.from_user.id
    
    try:
        await create_new_user(
            tg_id=tg_id,
            fio=data['fio'],
            room=data['room'],
            id_card=int(message.text)
        )
        # Локализовано
        await message.answer(
            t["reg_success"],
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    except Exception as e:
        # Локализовано
        error_message = str(e).split('>')[1] if '<class' in str(e) else str(e)
        await message.answer(f"{t['reg_db_error']}{error_message}")


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