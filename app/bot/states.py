from aiogram.fsm.state import StatesGroup, State

class AddRecord(StatesGroup):
    waiting_for_year = State()
    waiting_for_month = State()
    waiting_for_day = State()
    waiting_for_time = State()

class CancleRecord(StatesGroup):
    waiting_for_cancle = State()

class DisplayRecords(StatesGroup):
    waiting_for_display = State()

# --- Добавляем этот класс ---
class Registration(StatesGroup):
    waiting_for_fio = State()      # Ждем ФИО
    waiting_for_room = State()     # Ждем комнату
    waiting_for_id_card = State()  # Ждем номер зачетки