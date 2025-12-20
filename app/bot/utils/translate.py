from aiogram.fsm.context import FSMContext
from app.locales import ru, en, cn

ALL_TEXTS = {**ru.RUtexts, **en.ENtexts, **cn.CNtexts}

async def get_lang_and_texts(state: FSMContext) -> tuple[str, dict]:
    data = await state.get_data()
    lang = data.get('lang', 'RU')
    return lang, ALL_TEXTS.get(lang, ALL_TEXTS['RU'])