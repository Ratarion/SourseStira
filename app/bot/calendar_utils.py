# app/bot/calendar_utils.py
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

class CustomLaundryCalendar(SimpleCalendar):
    def __init__(self, workload: dict, max_capacity: int, locale: str = 'ru'):
        # Передаем show_alerts=True, чтобы библиотека сама не глушила навигацию, если мы этого не хотим
        super().__init__(locale=locale, show_alerts=True)
        self.workload = workload
        self.max_capacity = max_capacity

    async def start_calendar(self, year: int = datetime.now().year, month: int = datetime.now().month) -> InlineKeyboardMarkup:
        # 1. Генерируем стандартный календарь
        markup = await super().start_calendar(year, month)
        
        # 2. Модифицируем кнопки дней
        new_inline_keyboard = []
        
        for row in markup.inline_keyboard:
            new_row = []
            for btn in row:
                # Проверяем, что это кнопка дня (текст - число)
                # И callback_data не является игнорируемым (например, пустые дни)
                if btn.text.isdigit() and btn.callback_data:
                    day = int(btn.text)
                    
                    # Данные о загрузке
                    used = self.workload.get(day, 0)
                    # Если capacity 0 (нет машин), то свободных 0
                    free = self.max_capacity - used if self.max_capacity > 0 else 0
                    
                    # Логика раскраски
                    if free <= 0:
                        btn.text = f"{day} 🔴"  # Занято
                        # Опционально: можно сделать кнопку неактивной для нажатия,
                        # но лучше оставить, чтобы вывести алерт "Мест нет"
                    elif used == 0:
                        btn.text = f"{day} 🟢"  # Свободно
                    else:
                        # Частично занято (можно добавить кол-во мест, но текст может не влезть)
                        btn.text = f"{day} 🟡" 
                
                new_row.append(btn)
            new_inline_keyboard.append(new_row)
        
        markup.inline_keyboard = new_inline_keyboard
        return markup