from aiogram.types import {ReplyKeyboardMarkup, 
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           KeyboardButton}

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
            InlineKeyboardButton(text="Отменить запись", callback_data="show__records")
        ],
    ]
)

deg

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