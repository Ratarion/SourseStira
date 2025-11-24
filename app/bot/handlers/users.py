from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from app.bot.states import Registration, AddRecord
from app.bot.keyboards import section, get_time_slots_keyboard, get_machines_keyboard # Убедитесь, что section есть в keyboards
from app.repositories.laundry_repo import (
    get_user_by_tg_id, 
    create_new_user,
    get_available_slots, 
    get_all_machines, 
    is_slot_free, 
    create_booking
)

user_router = Router()

# ---------------------------------------------------------
# Смена языка
# ---------------------------------------------------------

# Обработка кнопки "Смены языка"
@user_router.callback_query(F.data == "ChangeLangeugeRU")
async def start_record(callback: CallbackQuery, state: FSMContext):
    
    await callback.message.answer("Смена языка на ENG (функция в разработке)") 
    # Здесь вы обычно вызываете функцию показа календаря

# ---------------------------------------------------------
# ЛОГИКА РЕГИСТРАЦИИ
# ---------------------------------------------------------

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    existing_user = await get_user_by_tg_id(tg_id)

    if existing_user:
        await message.answer(
            f"Здравствуйте, {existing_user.first_name}! Выберите действие:",
            reply_markup=section
        )
    else:
        await message.answer(
            "Здравствуйте! Давайте зарегистрируемся.\n\n"
            "Введите ваши <b>ФИО</b> через пробел:\n"
            "<i>Пример: Иванов Иван Иванович</i>"
        )
        await state.set_state(Registration.waiting_for_fio)

@user_router.message(Registration.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) < 3:
        await message.answer("Пожалуйста, введите Фамилию, Имя и Отчество через пробел.")
        return

    await state.update_data(fio=parts)
    await message.answer("Принято! Теперь введите <b>номер комнаты</b> (только цифры):")
    await state.set_state(Registration.waiting_for_room)

@user_router.message(Registration.waiting_for_room)
async def process_room(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Номер комнаты должен быть числом.")
        return

    await state.update_data(room=int(message.text))
    await message.answer("Введите <b>номер зачетной книжки</b>:")
    await state.set_state(Registration.waiting_for_id_card)

@user_router.message(Registration.waiting_for_id_card)
async def process_id_card(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Номер зачетки должен быть числом.")
        return

    data = await state.get_data()
    tg_id = message.from_user.id
    
    # Сохраняем в БД
    try:
        await create_new_user(
            tg_id=tg_id,
            fio=data['fio'],
            room=data['room'],
            id_card=int(message.text)
        )
        await message.answer(
            "Регистрация успешна! Добро пожаловать.",
            reply_markup=section
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка при сохранении: {e}")


# ---------------------------------------------------------
# ЛОГИКА ЗАПИСИ НА СТИРКУ
# ---------------------------------------------------------

# Обработка кнопки "Записаться" (нужно добавить callback в keyboards.py или проверить его)
@user_router.callback_query(F.data == "record")
async def start_record(callback: CallbackQuery, state: FSMContext):
    # Тут должна быть логика выбора года/месяца, или сразу отправка календаря
    # Для примера просто заглушка или переход к выбору
    await callback.message.answer("Выберите дату (функция в разработке)") 
    # Здесь вы обычно вызываете функцию показа календаря


# Ваш код выбора дня
@user_router.callback_query(F.data.startswith("day_"))
async def process_day(callback: CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    date = datetime(int(year), int(month), int(day))

    await state.update_data(chosen_date=date.date())

    slots = await get_available_slots(date)
    if not slots:
        await callback.message.edit_text(
            f"На {date.strftime('%d.%m.%Y')} нет свободных слотов",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_month")]
            ])
        )
        return

    await callback.message.edit_text(
        f"Выберите время на {date.strftime('%d.%m.%Y')}:",
        reply_markup=get_time_slots_keyboard(date, slots)
    )
    await state.set_state(AddRecord.waiting_for_time)

# Ваш код выбора времени
@user_router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    _, y, m, d, h = callback.data.split("_")
    chosen_dt = datetime(int(y), int(m), int(d), int(h))

    await state.update_data(start_time=chosen_dt)

    machines = await get_all_machines()
    available_machines = []
    for machine in machines:
        if await is_slot_free(machine.id, chosen_dt):
            available_machines.append(machine)

    if not available_machines:
        await callback.message.edit_text("Упс! Все машины заняты в это время.")
        return

    await callback.message.edit_text(
        f"Выберите стиральную машину на {chosen_dt.strftime('%d.%m %H:%M')}:",
        reply_markup=get_machines_keyboard(available_machines)
    )

# Ваш код создания брони
@user_router.callback_query(F.data.startswith("machine_"))
async def process_machine(callback: CallbackQuery, state: FSMContext):
    machine_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    start_time = data["start_time"]
    
    # Получаем юзера из базы (он уже точно есть, т.к. прошел регистрацию)
    user = await get_user_by_tg_id(callback.from_user.id)

    try:
        booking = await create_booking(
            user_id=user.id,
            machine_id=machine_id,
            start_time=start_time
        )
        await callback.message.edit_text(
            f"Запись создана!\n"
            f"Машина №{booking.machine.number_machine}\n"
            f"{start_time.strftime('%d.%m.%Y %H:%M')} – "
            f"{(start_time + timedelta(hours=2)).strftime('%H:%M')}",
            reply_markup=section # Возвращаем меню
        )
    except ValueError:
        await callback.message.edit_text("Слот уже занят другим пользователем!")
    
    await state.clear()