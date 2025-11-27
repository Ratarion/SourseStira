# app/bot/calendar_utils.py
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram.filters.callback_data import CallbackData

class CustomLaundryCalendarCallback(CallbackData, prefix="custom_laundry_calendar"):
    act: str
    year: int
    month: int
    day: int

# Изменения в calendar_utils.py (Календарь)
class CustomLaundryCalendar(SimpleCalendar):
    calendar_callback = CustomLaundryCalendarCallback

    def __init__(self, workload: dict, max_capacity: int, locale: str = 'ru'):
        super().__init__(locale=locale, show_alerts=True)
        self.workload = workload
        self.max_capacity = max_capacity
        self._current_year = datetime.now().year
        self._current_month = datetime.now().month

    async def start_calendar(self, year: int = datetime.now().year, month: int = datetime.now().month) -> InlineKeyboardMarkup:
        year = self._current_year
        month = self._current_month
        
        markup = await super().start_calendar(year, month)
        
        new_inline_keyboard = []
        
        for row in markup.inline_keyboard:
            new_row = []
            for btn in row:
                if btn.text.isdigit() and btn.callback_data:
                    day = int(btn.text)
                    used = self.workload.get(day, 0)
                    free = self.max_capacity - used if self.max_capacity > 0 else 0
                    
                    if free <= 0:
                        btn.text = f"{day} 🔴"
                    elif used == 0:
                        btn.text = f"{day} 🟢"
                    else:
                        btn.text = f"{day} 🟡" 
                
                new_row.append(btn)
            new_inline_keyboard.append(new_row)
            
        header_row = markup.inline_keyboard[0]
        month_year_button = header_row[1]
        
        new_header_row = [
             InlineKeyboardButton(text=month_year_button.text, callback_data='ignore_nav')
        ]
        
        final_inline_keyboard = [new_header_row]
        
        for row in markup.inline_keyboard[1:]:
            new_row = []
            for btn in row:
                if btn.text.isdigit() and btn.callback_data:
                    day = int(btn.text)
                    used = self.workload.get(day, 0)
                    free = self.max_capacity - used if self.max_capacity > 0 else 0
                    
                    if free <= 0:
                        btn.text = f"{day} 🔴"
                    elif used == 0:
                        btn.text = f"{day} 🟢"
                    else:
                        btn.text = f"{day} 🟡"
                
                new_row.append(btn)
            final_inline_keyboard.append(new_row)

        return InlineKeyboardMarkup(inline_keyboard=final_inline_keyboard)
