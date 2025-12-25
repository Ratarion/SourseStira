from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.repositories.laundry_repo import get_booking_by_id, set_booking_status
from app.bot.utils.translate import ALL_TEXTS

confirm_router = Router()

@confirm_router.callback_query(F.data.startswith("confirm_"))
async def process_confirm(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    
    # Получаем бронь, чтобы узнать язык юзера (или берем из контекста, если юзер тот же)
    booking = await get_booking_by_id(booking_id)
    
    # Определяем язык (здесь берем дефолт RU, так как state может не быть, но можно достать из user repo)
    # Для простоты можно взять RU или попробовать достать язык из callback.from_user
    # Но лучше всего передавать тексты, если они простые.
    # Допустим, мы берем стандартный текст, так как не используем FSMContext
    t = ALL_TEXTS["RU"] 
    
    if not booking:
        await callback.answer(t["booking_already_confirmed"], show_alert=True)
        await callback.message.delete()
        return

    if booking.status == 'confirmed':
         await callback.answer(t["booking_already_confirmed"], show_alert=True)
         # Можно удалить кнопку
         await callback.message.edit_reply_markup(reply_markup=None)
         return

    # Обновляем статус
    await set_booking_status(booking_id, "confirmed")
    
    await callback.message.edit_text(t["booking_confirmed"])
    await callback.answer()