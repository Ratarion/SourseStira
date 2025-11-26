from aiogram.fsm.state import StatesGroup, State

# --- Запись на стирку ---
class AddRecord(StatesGroup):
    waiting_for_year = State()
    waiting_for_month = State()
    waiting_for_day = State()
    waiting_for_time = State()

# --- Вход ---
class Welcome(StatesGroup):
    waiting_for_client = State()

class CancelRecord(StatesGroup):
    waiting_for_cancel = State()

class DisplayRecords(StatesGroup):
    waiting_for_display = State()


# --- Аунтификация ---
class Auth(StatesGroup):
    waiting_for_fio = State()      # Ждем ФИО для проверки
    waiting_for_id_card = State()  # Если ФИО нет, ждем зачетку