from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot
from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.repositories.laundry_repo import get_or_create_user, is_slot_free
from aiogram.types import CallbackQuery, Message

from app.repositories.laundry_repo import (
    get_available_slots,
    get_all_machines,
    create_booking,
    get_user_bookings,
    cancel_booking
)
from app.bot.keyboards import get_time_slots_keyboard, get_machines_keyboard
from app.bot.states import AddRecord

from app.config import config as cfg

user_router = Router(name="user_router")
bot = Bot(token=cfg.BOT_TOKEN)




router = Router()


# Шаг 1: Выбор года → месяца → дня (уже есть у тебя)
# После выбора дня:
@router.callback_query(F.data.startswith("day_"))
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


# Шаг 2: Выбор времени
@router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    _, y, m, d, h = callback.data.split("_")
    chosen_dt = datetime(int(y), int(m), int(d), int(h))

    await state.update_data(start_time=chosen_dt)

    # Находим свободные машины в этот слот
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


# Шаг 3: Выбор машины → создание брони
@router.callback_query(F.data.startswith("machine_"))
async def process_machine(callback: CallbackQuery, state: FSMContext):
    machine_id = int(callback.data.split("_")[1])
    data = await state.get_data()

    user = await get_or_create_user(...)  # получаешь из контекста или БД по tg_id
    start_time = data["start_time"]

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
            f"{(start_time + timedelta(hours=2)).strftime('%H:%M')}"
        )
    except ValueError:
        await callback.message.edit_text("Слот уже занят другим пользователем!")
    
    await state.clear()