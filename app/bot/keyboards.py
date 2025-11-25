from aiogram.types import (InlineKeyboardMarkup,
                           InlineKeyboardButton)
from datetime import datetime
# ИМПОРТ: Добавлен cn
from app.locales import ru, en, cn 

# Объединяем словари локализации
ALL_TEXTS = {**ru.RUtexts, **en.ENtexts, **cn.CNtexts} 

# Словарь месяцев для календаря (если используется)
months = {
    1: {"RU": "Январь", "ENG": "January", "CN": "一月"},
    2: {"RU": "Февраль", "ENG": "February", "CN": "二月"},
    3: {"RU": "Март", "ENG": "March", "CN": "三月"},
    4: {"RU": "Апрель", "ENG": "April", "CN": "四月"},
    5: {"RU": "Май", "ENG": "May", "CN": "五月"},
    6: {"RU": "Июнь", "ENG": "June", "CN": "六月"},
    7: {"RU": "Июль", "ENG": "July", "CN": "七月"},
    8: {"RU": "Август", "ENG": "August", "CN": "八月"},
    9: {"RU": "Сентябрь", "ENG": "September", "CN": "九月"},
    10: {"RU": "Октябрь", "ENG": "October", "CN": "十月"},
    11: {"RU": "Ноябрь", "ENG": "November", "CN": "十一月"},
    12: {"RU": "Декабрь", "ENG": "December", "CN": "十二月"}
}

# Клавиатура выбора языка
kb_welcom = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='RU', callback_data='lang_RU'),
        InlineKeyboardButton(text="ENG", callback_data='lang_ENG'), 
        InlineKeyboardButton(text='CN', callback_data='lang_CN')
    ]
])

def get_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"]) # Дефолт - RU
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["record_laundry"], callback_data="record"),
                InlineKeyboardButton(text=t["show_records"], callback_data="show_records"),
                InlineKeyboardButton(text=t["cancel_record"], callback_data="remove_records"),
            ],
        ]
    )

def get_exit_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["exit"], callback_data="exit")
            ],
        ]
    )

# Клавиатура выбора года (функция getYaersButton переименована).
def get_years_button(years: list, lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    yearsButton = [
        [InlineKeyboardButton(text=f"{year}", callback_data=f"year_{year}")]
        for year in years
    ]
    yearsButton.append([InlineKeyboardButton(text=t["exit"], callback_data="exit")])
    return InlineKeyboardMarkup(inline_keyboard=yearsButton)

# Клавиатура выбора времени.
def get_time_slots_keyboard(date: datetime, slots: list[datetime], lang: str) -> InlineKeyboardMarkup:
    t = ALL_TEXTS.get(lang, ALL_TEXTS["RU"])
    buttons = []
    for slot in slots:
        text = slot.strftime("%H:%M")
        callback = f"time_{date.year}_{date.month}_{date.day}_{slot.hour}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])

    buttons.append([InlineKeyboardButton(text=t["back"], callback_data="back_to_calendar")])
    buttons.append([InlineKeyboardButton(text=t["exit"], callback_data="exit")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура выбора машины.
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