from aiogram.fsm.state import StatesGroup, State

# --- Запись на стирку ---
class AddRecord(StatesGroup):
    waiting_for_machine_type = State() 
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_machine = State()
    
# --- Вход ---
class Welcome(StatesGroup):
    waiting_for_client = State()

class Report(StatesGroup):
    waiting_for_report = State()

class CancelRecord(StatesGroup):
    waiting_for_cancel = State()

class DisplayRecords(StatesGroup):
    waiting_for_display = State()


# --- Аунтификация ---
class Auth(StatesGroup):
    waiting_for_fio = State()      # Ждем ФИО для проверки
    waiting_for_id_card = State()  # Если ФИО нет, ждем зачетку