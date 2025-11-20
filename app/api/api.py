# # НУЖНО: вызов функции базы данных
# import sqlite3
# from bot_handlers.users import user_router

# from database import db_commands  # Предполагаемый модуль с вашими SQL запросами

# @user_router.message(F.text == "Записаться на стирку")
# async def book_machine(message: Message):
#     user_id = message.from_user.id
    
#     # 1. Проверяем, есть ли свободные машины (логика из ТЗ)
#     free_slots = await db_commands.get_available_slots()
    
#     if not free_slots:
#         await message.answer("Свободных машин нет.")
#         return

#     # 2. Показываем слоты (клавиатура)
#     await message.answer("Выберите время:", reply_markup=kb.create_slots_keyboard(free_slots))

# async def get_available_slots():
#     # Здесь подключение к БД и запрос. Для теста вернём фейковые слоты
#     return ["10:00", "12:00"]  # Замените на реальную логику