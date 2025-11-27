from aiogram.types import (InlineKeyboardMarkup,
                           InlineKeyboardButton)
from datetime import datetime, timedelta
from app.locales import ru, en, cn 

# Объединяем словари локализации
ALL_TEXTS = {**ru.RUtexts, **en.ENtexts, **cn.CNtexts} 

kb_welcom = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='RU', callback_data='lang_RU'),
        InlineKeyboardButton(text="ENG", callback_data='lang_ENG'), 
        InlineKeyboardButton(text='CN', callback_data='lang_CN')
    ]
])

# Клавиатура для выбора типа машины: стирка или сушка.
def get_machine_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            # callback_data: type_WASH (стирка) или type_DRY (сушка)
            [InlineKeyboardButton(text=t["machine_type_wash"], callback_data="type_WASH")],
            [InlineKeyboardButton(text=t["machine_type_dry"], callback_data="type_DRY")],
            [InlineKeyboardButton(text=t["back"], callback_data="back_to_sections")] # Назад в главное меню
        ]
    )

def get_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["record_laundry"], callback_data="record")],
            [InlineKeyboardButton(text=t["show_records"], callback_data="show_records")],
            [InlineKeyboardButton(text=t["cancel_record"], callback_data="remove_records")],
            [InlineKeyboardButton(text=t["report_in_admin"], callback_data="report")],
        ]
    )

def get_exit_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t["exit"], callback_data="exit")]])


def get_machines_keyboard(available_machines: list, lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    buttons = [
        [InlineKeyboardButton(
            text=f"№{m.number_machine} ({t['machine_type']}: {m.type_machine})",
            callback_data=f"machine_{m.id}"
        )]
        for m in available_machines
    ]
    buttons.append([InlineKeyboardButton(text=t["back"], callback_data="back_to_time")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#Вывод промежутка времени 8:00-9:30
def get_time_slots_keyboard(date: datetime, slots: list[datetime], lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    buttons = []

    DURATION = timedelta(minutes=90) # Длительность одной записи - 90 минут

    for slot in slots:
        start_time = slot
        end_time = start_time + DURATION

        # Формат времени: "08:00 - 09:30"
        text = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

        # Используем новый формат callback_data
        callback = f"time_{date.year}_{date.month}_{date.day}_{slot.hour}_{slot.minute}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])

    buttons.append([InlineKeyboardButton(text=t["back"], callback_data="back_to_calendar")])
    buttons.append([InlineKeyboardButton(text=t["exit"], callback_data="exit")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)