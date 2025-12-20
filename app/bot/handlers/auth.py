from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import kb_welcom, get_section_keyboard
from app.repositories.laundry_repo import (
    get_user_by_tg_id,
    find_resident_by_fio,
    find_resident_by_id_card,
    activate_resident_user
)
from app.bot.states import Auth
from  app.bot.utils.translate import get_lang_and_texts, ALL_TEXTS

auth_router = Router()

@auth_router.message(CommandStart())
async def cmd_start_initial(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'lang' not in data:
        await message.answer(
            ALL_TEXTS["RU"]["welcome_lang_choice"],  # Полный мультиязычный текст
            reply_markup=kb_welcom
        )
    else:
        await cmd_start_auth(message, state)

@auth_router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    # удаляем сообщение выбора языка и запускаем авторизацию
    await callback.message.delete()
    await cmd_start_auth(callback.message, state)

async def cmd_start_auth(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    existing_user = await get_user_by_tg_id(tg_id)
    lang, t = await get_lang_and_texts(state)

    if existing_user:
        await message.answer(
            t['hello_user'].format(name=existing_user.first_name),
            reply_markup=get_section_keyboard(lang)
        )
    else:
        await message.answer(t["auth"])
        await state.set_state(Auth.waiting_for_fio)

@auth_router.message(Auth.waiting_for_fio)
async def process_fio_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    text = message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer(t["write_FIO"])
        return
    resident = await find_resident_by_fio(parts)
    if resident:
        if resident.tg_id and resident.tg_id != message.from_user.id:
            await message.answer(t["other_tg_id"])
            return
        await activate_resident_user(resident.id, message.from_user.id)
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}",
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    else:
        await message.answer(t["seek_cards"])
        await state.set_state(Auth.waiting_for_id_card)

@auth_router.message(Auth.waiting_for_id_card)
async def process_id_card_auth(message: Message, state: FSMContext):
    lang, t = await get_lang_and_texts(state)
    if not message.text.isdigit():
        await message.answer(t["reg_id_error"])
        return
    id_card_num = int(message.text)
    from app.repositories.laundry_repo import find_resident_by_id_card, activate_resident_user
    resident = await find_resident_by_id_card(id_card_num)
    if resident:
        if resident.tg_id and resident.tg_id != message.from_user.id:
            await message.answer(t["other_tg_id"])
            return
        await activate_resident_user(resident.id, message.from_user.id)
        await message.answer(
            f"{t['hello_user'].replace('{name}', resident.first_name)}",
            reply_markup=get_section_keyboard(lang)
        )
        await state.clear()
        await state.update_data(lang=lang)
    else:
        await message.answer(t["none_user"])