from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_calendar import SimpleCalendar
from aiogram.filters.callback_data import CallbackData

class CustomLaundryCalendarCallback(CallbackData, prefix="custom_laundry_calendar"):
    act: str
    year: int
    month: int
    day: int

class CustomLaundryCalendar(SimpleCalendar):
    calendar_callback = CustomLaundryCalendarCallback

    def __init__(self, workload: dict, max_capacity: int, locale: str = 'ru'):
        super().__init__(locale=locale, show_alerts=True)
        self.workload = workload
        self.max_capacity = max_capacity
        
        self.months_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }

    async def start_calendar(self, year: int = None, month: int = None) -> InlineKeyboardMarkup:
        # Всегда берем текущую дату
        now = datetime.now()
        curr_year = now.year
        curr_month = now.month
    
        # Генерируем базовую структуру (она содержит Год, Навигацию, Дни недели, Дни, Футер)
        markup = await super().start_calendar(year=curr_year, month=curr_month)
        original_kb = markup.inline_keyboard
        
        new_inline_keyboard = []
    
        # 1. СТРОКА ЗАГОЛОВКА (Только месяц)
        # Вместо [ < ] [ Месяц ] [ > ] создаем одну кнопку с именем месяца
        month_name = self.months_names.get(curr_month, "Месяц")
        title_btn = InlineKeyboardButton(text=month_name, callback_data="ignore_action")
        new_inline_keyboard.append([title_btn])

        # 2. СТРОКА ДНИ НЕДЕЛИ (Пн, Вт, Ср...)
        # В стандартном SimpleCalendar:
        # index 0 = Год [2025] -> пропускаем
        # index 1 = Навигация [<][дек][>] -> мы заменили её своим заголовком выше
        # index 2 = Дни недели -> берем
        if len(original_kb) > 2:
            new_inline_keyboard.append(original_kb[2])

        # 3. СТРОКИ С ДАТАМИ (1, 2, 3...)
        # Даты идут с 3-го индекса и до предпоследнего (последний - это Cancel/Today)
        # Мы итерируемся от 3 до len-1, чтобы отсечь футер
        for row in original_kb[3:-1]:
            new_row = []
            for btn in row:
                # Логика раскраски кружочков
                if btn.text.isdigit():
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
    
        return InlineKeyboardMarkup(inline_keyboard=new_inline_keyboard)