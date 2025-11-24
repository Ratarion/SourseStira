from aiogram.types import (ReplyKeyboardMarkup, 
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           KeyboardButton)
from datetime import datetime

months = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}



section = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Записаться на стирку", callback_data="record"),
            InlineKeyboardButton(text="Показать мои записи", callback_data="show_records"),
            InlineKeyboardButton(text="Отменить запись", callback_data="show__records"),
            InlineKeyboardButton(text="RU", callback_data="ChangeLangeugeRU"),
            InlineKeyboardButton(text="ENG", callback_data="ChangeLangeugeENG")
        ],
    ]
)


exit = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Выйти", callback_data="exit")
        ],
    ]
)

def getYaersButton(years: list):
    yearsButton = [
        [InlineKeyboardButton(text=f"{year}", callback_data=f"year_{year}")]
        for year in years
    ]
    yearsButton.append([InlineKeyboardButton(text="Выйти", callback_data="exit")])
    return InlineKeyboardMarkup(inline_keyboard=yearsButton)

def get_time_slots_keyboard(date: datetime, slots: list[datetime]) -> InlineKeyboardMarkup:
    buttons = []
    for slot in slots:
        text = slot.strftime("%H:%M")
        callback = f"time_{date.year}_{date.month}_{date.day}_{slot.hour}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])

    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_calendar")])
    buttons.append([InlineKeyboardButton(text="Выйти", callback_data="exit")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_machines_keyboard(available_machines: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"№{m.number_machine} ({m.type_machine})",
            callback_data=f"machine_{m.id}"
        )]
        for m in available_machines
    ]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_time")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)