from datetime import datetime, time
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
        # Ensure locale is lowercase for consistency
        super().__init__(locale=locale.lower(), show_alerts=True)
        self.workload = workload
        self.max_capacity = max_capacity
        self.locale = locale.lower()
        
        self.months_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        
        # Simple translation map for the Back button inside the class
        self.back_labels = {
            'ru': "Назад",
            'en': "Back",
            'cn': "返回",
            'zh': "返回"
        }

    async def start_calendar(
        self, 
        year: int = None, 
        month: int = None, 
        header_text: str = None, 
        back_callback: str = None
    ) -> InlineKeyboardMarkup:
        
        # Determine current date if not provided
        now = datetime.now()
        if year is None: year = now.year
        if month is None: month = now.month
    
        # Generate base structure from SimpleCalendar
        markup = await super().start_calendar(year=year, month=month)
        original_kb = markup.inline_keyboard
        
        new_inline_keyboard = []
    
        # 1. HEADER ROW (Month Name)
        # We prefer keeping the Month name as the header so the user knows which month acts.
        # If you strictly want 'header_text' to replace the month name, uncomment the next line:
        # title_text = header_text if header_text else self.months_names.get(month, "Month")
        title_text = self.months_names.get(month, "Месяц")
        
        title_btn = InlineKeyboardButton(text=title_text, callback_data="ignore_action")
        new_inline_keyboard.append([title_btn])

        # 2. WEEKDAYS ROW
        # In SimpleCalendar: index 2 usually contains weekdays (Mo, Tu, We...)
        if len(original_kb) > 2:
            new_inline_keyboard.append(original_kb[2])

        # 3. DATE ROWS
        # SimpleCalendar usually puts days from index 3 up to the footer.
        # We iterate to find rows containing days (digits).
        for row in original_kb[3:]:
            new_row = []
            has_days = False
            for btn in row:
                # Check if this button is a day number
                if btn.text.isdigit():
                    has_days = True
                    day = int(btn.text)
                    used = self.workload.get(day, 0)
                    free = self.max_capacity - used if self.max_capacity > 0 else 0

                    now_dt = datetime.now()
                    today_date = now_dt.date()
                    now_time = now_dt.time()

                    current_day = datetime(year, month, day).date()

                    if current_day < today_date or (current_day == today_date and now_time >= time(23, 0)):
                        btn.text = f"{day} ⚪"
                    elif free <= 0:
                        btn.text = f"{day} 🔴"
                    elif used == 0:
                        btn.text = f"{day} 🟢"
                    else:
                        btn.text = f"{day} 🟡"
                
                # Filter out standard navigation buttons if you don't want them (Cancel, Today)
                # or keep them if they are part of the day rows.
                new_row.append(btn)
            
            # Only append the row if it actually contains calendar days or valid spacers
            if has_days:
                new_inline_keyboard.append(new_row)

        # 4. BACK BUTTON (Footer)
        if back_callback:
            back_label = self.back_labels.get(self.locale, "Back")
            back_btn = InlineKeyboardButton(text=f"⬅️ {back_label}", callback_data=back_callback)
            new_inline_keyboard.append([back_btn])
    
        return InlineKeyboardMarkup(inline_keyboard=new_inline_keyboard)