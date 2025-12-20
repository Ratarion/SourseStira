# app/bot/handlers/booking.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, time, timedelta
from aiogram.exceptions import TelegramBadRequest
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
try:
    from aiogram_calendar.schemas import SimpleCalendarAction
except ImportError:
    class SimpleCalendarAction:
        DAY = "DAY"

from app.bot.utils.translate import get_lang_and_texts

from app.bot.calendar_utils import CustomLaundryCalendar
from app.bot.states import AddRecord
from app.bot.keyboards import (
    get_section_keyboard,
    get_time_slots_keyboard,
    get_machines_keyboard,
    get_exit_keyboard,
    get_machine_type_keyboard
)
from app.repositories.laundry_repo import (
    get_user_by_tg_id,
    get_available_slots,
    get_available_machines,
    is_slot_free,
    create_booking,
    get_month_workload,
    get_total_daily_capacity_by_type,
    get_user_bookings
)

booking_router = Router()

# helper for colored calendar (можно использовать если нужно создать календарь отдельно)
async def get_colored_calendar(year: int, month: int, locale: str, machine_type=None):
    workload = await get_month_workload(year, month, machine_type)
    max_slots = await get_total_daily_capacity_by_type(machine_type)
    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_slots, locale=locale)
    return await calendar.start_calendar(year=year, month=month)


@booking_router.callback_query(F.data == "record")
async def process_record_start(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    max_capacity = await get_total_daily_capacity_by_type()
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


@booking_router.callback_query(F.data.startswith("type_"), AddRecord.waiting_for_machine_type)
async def process_machine_type(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    machine_type_callback = callback.data.split("_")[1]
    if machine_type_callback == "WASH":
        machine_type_db = t["machine_type_wash"]
        header_text = f"📅 {t['record_start']} {t['for_wash']}"
    else:
        machine_type_db = t["machine_type_dry"]
        header_text = f"📅 {t['record_start']} {t['for_dry']}"

    await state.update_data(machine_type=machine_type_db)
    now = datetime.now()
    workload = await get_month_workload(now.year, now.month, machine_type_db)
    max_capacity = await get_total_daily_capacity_by_type(machine_type_db)
    await state.update_data(max_capacity=max_capacity)

    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_capacity, locale=lang.lower())
    await callback.message.edit_text(
        header_text,
        reply_markup=await calendar.start_calendar(
            year=now.year, month=now.month, header_text=header_text, back_callback="back_to_sections"
        )
    )
    await state.set_state(AddRecord.waiting_for_day)
    await callback.answer()


@booking_router.callback_query(SimpleCalendarCallback.filter(F.act == "DAY"), AddRecord.waiting_for_day)
async def process_simple_calendar(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    max_capacity = data.get('max_capacity', 0)
    machine_type_db = data.get('machine_type')
    workload = await get_month_workload(callback_data.year, callback_data.month, machine_type_db)
    calendar = CustomLaundryCalendar(workload=workload, max_capacity=max_capacity, locale=lang.lower())

    # предполагается, что CustomLaundryCalendar возвращает (selected, date) при process_selection
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected and callback_data.act == SimpleCalendarAction.DAY:
        now_dt = datetime.now()
        if date.date() < now_dt.date() or (date.date() == now_dt.date() and now_dt.time() >= time(23, 0)):
            await callback.answer(t["past_date_error"], show_alert=True)
            await callback.message.edit_text(
                t["record_start"],
                reply_markup=await calendar.start_calendar(year=callback_data.year, month=callback_data.month, back_callback="back_to_machine_type")
            )
            await state.set_state(AddRecord.waiting_for_day)
            return

        day = date.day
        used = workload.get(day, 0)
        free = max_capacity - used if max_capacity > 0 else 0
        if free <= 0:
            await callback.answer(t["day_fully_booked"], show_alert=True)
            await callback.message.edit_text(
                t["record_start"],
                reply_markup=await calendar.start_calendar(year=callback_data.year, month=callback_data.month, back_callback="back_to_machine_type")
            )
            await state.set_state(AddRecord.waiting_for_day)
            return

        await state.update_data(chosen_date=date)
        slots = await get_available_slots(date, machine_type=machine_type_db)
        if not slots:
            await callback.answer(t["no_slots_available"], show_alert=True)
            await callback.message.edit_text(
                t["record_start"],
                reply_markup=await calendar.start_calendar(year=callback_data.year, month=callback_data.month, back_callback="back_to_machine_type")
            )
            await state.set_state(AddRecord.waiting_for_day)
            return

        await callback.message.edit_text(
            t["select_time_prompt"].replace("{date}", date.strftime("%d.%m")),
            reply_markup=get_time_slots_keyboard(date, slots, lang)
        )
        await state.set_state(AddRecord.waiting_for_time)
        await callback.answer()
        return

    await callback.answer()


# Код выбора времени — заменил user_router на booking_router
@booking_router.callback_query(F.data.startswith("time_"), AddRecord.waiting_for_time)
async def process_time_slot(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()

    parts = callback.data.split("_")
    # ожидаем формат time_YEAR_MONTH_DAY_HOUR_MINUTE
    year, month, day, hour, minute = map(int, parts[1:6])
    chosen_dt = datetime(year, month, day, hour, minute)

    await state.update_data(start_time=chosen_dt)

    machine_type_db = data.get('machine_type')
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


@booking_router.callback_query(F.data.startswith("machine_"), AddRecord.waiting_for_machine)
async def process_machine(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    machine_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    duration_minutes = 90
    start_time = data["start_time"]
    end_time = start_time + timedelta(minutes=duration_minutes)

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer(t["not_authenticated"], show_alert=True)
        return

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
            await state.update_data(lang=lang)
            return
        else:
            await callback.answer(t["slot_just_taken"], show_alert=True)

    except Exception as e:
        # лог можно добавить: logging.exception(e)
        await callback.message.edit_text(t["booking_error"])

    # на всякий случай освобождаем стейт
    await state.clear()
    await state.update_data(lang=lang)


@booking_router.callback_query(F.data == "back_to_sections", AddRecord.waiting_for_machine_type)
async def process_back_to_sections(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await state.clear()
    await callback.answer()


@booking_router.callback_query(F.data == "back_to_calendar", AddRecord.waiting_for_time)
async def process_back_to_calendar(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    machine_type_db = data.get('machine_type')
    max_capacity = data.get('max_capacity', 0)
    now = datetime.now()
    workload = await get_month_workload(now.year, now.month, machine_type_db)

    calendar = CustomLaundryCalendar(
        workload=workload,
        max_capacity=max_capacity,
        locale=lang.lower()
    )

    # Generate header text to be consistent
    if machine_type_db == t.get("machine_type_wash"):
         header_text = f"📅 {t['record_start']} {t['for_wash']}"
    else:
         header_text = f"📅 {t['record_start']} {t['for_dry']}"

    await callback.message.edit_text(
        header_text,
        reply_markup=await calendar.start_calendar(
            year=now.year,
            month=now.month,
            header_text=header_text,
            back_callback="back_to_machine_type"
        )
    )
    await state.set_state(AddRecord.waiting_for_day)
    await callback.answer()


@booking_router.callback_query(F.data == "back_to_time", AddRecord.waiting_for_machine)
async def process_back_to_time(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    data = await state.get_data()
    chosen_date = data.get('chosen_date')
    if not chosen_date:
        await callback.answer("Дата не найдена", show_alert=True)
        return
    machine_type_db = data.get('machine_type')
    slots = await get_available_slots(chosen_date, machine_type=machine_type_db)
    await callback.message.edit_text(
        t["select_time_prompt"].replace("{date}", chosen_date.strftime("%d.%m")),
        reply_markup=get_time_slots_keyboard(chosen_date, slots, lang)
    )
    await state.set_state(AddRecord.waiting_for_time)
    await callback.answer()


@booking_router.callback_query(F.data == "exit")
async def process_exit(callback: CallbackQuery, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    await callback.message.edit_text(
        t["hello_user"].format(name=callback.from_user.first_name),
        reply_markup=get_section_keyboard(lang)
    )
    await state.clear()
    await callback.answer()


# # Отладочный / универсальный логгер колбэков (оставил, но на booking_router)
# @booking_router.callback_query()
# async def debug_callback(cb: CallbackQuery):
#     import logging
#     logging.info("Callback received: %s", cb.data)
#     await cb.answer()
