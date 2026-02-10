import logging
import asyncio
import random
import json
import os
from time import time
from datetime import timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from mistralai import Mistral

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8104909560:AAHUS88zCrxDukxqMIOZBMIhVE3M3G4WjP8"
MISTRAL_API_KEY = "Fl1fzomHyW03LF4LePSmwJnJTht0XKsl"
ADMIN_PASSWORD = "import"  # ЗАМЕНИ НА СВОЙ ПАРОЛЬ
CONFIG_FILE = "config.json"

# Твои оригинальные правила
ORIGINAL_RULES = """<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> <b>Правила чата</b>
<tg-emoji emoji-id="5424857974784925603">🚫</tg-emoji> Без спама и рекламы
<tg-emoji emoji-id="4916086774649848789">🔗</tg-emoji> Без ссылок без разрешения админа
<tg-emoji emoji-id="5352783059143901208">🖕</tg-emoji> Без оскорблений
<tg-emoji emoji-id="5877488510637706502">🚫</tg-emoji> Запрещены мошеннические схемы
<tg-emoji emoji-id="5318912942752669674">💻</tg-emoji> Запрещено просить взломать что либо
<tg-emoji emoji-id="5422789690333883156">ℹ️</tg-emoji> Запрещено писать не по делу, (просить инструменты для DOX\\OSINT)
<tg-emoji emoji-id="5258500400918587241">✍️</tg-emoji> Запрещено разговаривать на других языках кроме RU/ENG
<tg-emoji emoji-id="5206432422194849059">🔒</tg-emoji> Нарушение = мут / бан

А кто не согласен с правилами читать <a href="https://hhroot.alwaysdata.net/">здесь</a>"""

default_config = {
    "model": "open-mistral-7b",
    "prompt": "Ты — полезный ассистент в Telegram-чате S010lvloon. Отвечай кратко и по делу. Используй премиум эмодзи. Если тебя спрашивают про правила чата, напоминай про команду #rules.",
    "rules": ORIGINAL_RULES
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_config
    return default_config

def save_config(new_config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)

config = load_config()

class AdminStates(StatesGroup):
    waiting_for_password = State()
    main_menu = State()
    editing_prompt = State()
    editing_rules = State()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

user_cooldowns = {}
active_duels = {}

# --- ФУНКЦИЯ ГЕНЕРАЦИИ ГЛАВНОГО МЕНЮ АДМИНКИ ---
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить Промт", callback_data="edit_prompt")],
        [InlineKeyboardButton(text="📜 Изменить Правила", callback_data="edit_rules")],
        [InlineKeyboardButton(text="🤖 Изменить Модель", callback_data="edit_model")],
        [InlineKeyboardButton(text="❌ Выход", callback_data="exit_admin")]
    ])

# --- АДМИН ПАНЕЛЬ (/S2HFHF) ---

@dp.message(Command("S2HFHF"))
async def admin_auth(message: Message, state: FSMContext):
    await message.answer("🔒 Введите пароль доступа:")
    await state.set_state(AdminStates.waiting_for_password)

@dp.message(AdminStates.waiting_for_password)
async def check_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await state.set_state(AdminStates.main_menu)
        await message.answer(f"⚙️ <b>S010lvloon Admin</b>\nТекущая модель: <code>{config['model']}</code>", reply_markup=get_admin_kb())
    else:
        await message.answer("❌ Доступ запрещен.")
        await state.clear()

@dp.callback_query(F.data == "back_to_admin", AdminStates.main_menu)
async def back_to_admin(call: CallbackQuery):
    await call.message.edit_text(f"⚙️ <b>S010lvloon Admin</b>\nТекущая модель: <code>{config['model']}</code>", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "edit_prompt", AdminStates.main_menu)
async def start_edit_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(f"Текущий промт:\n<code>{config['prompt']}</code>\n\nПришли новый текст промта:")
    await state.set_state(AdminStates.editing_prompt)

@dp.message(AdminStates.editing_prompt)
async def save_prompt_logic(message: Message, state: FSMContext):
    config['prompt'] = message.text
    save_config(config)
    await message.answer("✅ Промт сохранен!", reply_markup=get_admin_kb())
    await state.set_state(AdminStates.main_menu)

@dp.callback_query(F.data == "edit_rules", AdminStates.main_menu)
async def start_edit_rules(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Пришли новый HTML текст правил (можешь использовать теги b, i, a, tg-emoji):")
    await state.set_state(AdminStates.editing_rules)

@dp.message(AdminStates.editing_rules)
async def save_rules_logic(message: Message, state: FSMContext):
    config['rules'] = message.text
    save_config(config)
    await message.answer("✅ Правила обновлены!", reply_markup=get_admin_kb())
    await state.set_state(AdminStates.main_menu)

@dp.callback_query(F.data == "edit_model", AdminStates.main_menu)
async def menu_model(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="open-mistral-7b (Дешево)", callback_data="set_m_open-mistral-7b")],
        [InlineKeyboardButton(text="mistral-small-latest", callback_data="set_m_mistral-small-latest")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_admin")]
    ])
    await call.message.edit_text("Выберите модель Mistral:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_m_"), AdminStates.main_menu)
async def save_model_logic(call: CallbackQuery):
    new_model = call.data.replace("set_m_", "")
    config['model'] = new_model
    save_config(config)
    await call.answer(f"Модель {new_model} активирована!")
    await call.message.edit_text(f"⚙️ <b>S010lvloon Admin</b>\nТекущая модель: <code>{config['model']}</code>", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "exit_admin")
async def exit_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🚪 Сессия закрыта.")

# --- ОСНОВНЫЕ ФУНКЦИИ ---

@dp.message(Command("ai"))
async def cmd_ai(message: Message):
    user_id = message.from_user.id
    if user_id in user_cooldowns and time() - user_cooldowns[user_id] < 15:
        return await message.reply("⏳ Подожди немного перед следующим вопросом.")
    
    prompt = message.text.replace("/ai", "").strip()
    if not prompt: return await message.reply("Напиши вопрос!")

    await bot.send_chat_action(message.chat.id, "typing")
    try:
        res = await asyncio.to_thread(
            mistral_client.chat.complete,
            model=config['model'],
            messages=[{"role": "system", "content": config['prompt']}, {"role": "user", "content": prompt}]
        )
        user_cooldowns[user_id] = time()
        text = res.choices[0].message.content.replace("<", "&lt;").replace(">", "&gt;")
        await message.reply(f"<blockquote>{text}</blockquote>")
    except Exception as e:
        await message.reply(f"❌ Ошибка ИИ: {e}")

@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.answer(config['rules'], disable_web_page_preview=True)

@dp.message(lambda m: m.text and "#rules" in m.text.lower())
async def tag_rules(message: Message):
    await message.reply(config['rules'], disable_web_page_preview=True)

@dp.message(Command("duel"))
async def cmd_duel(message: Message):
    if message.chat.type == "private":
        return await message.reply("🎮 Дуэли только в группах!")
    active_duels[message.chat.id] = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Принять вызов! 🤝", callback_data="accept_duel")]])
    await message.answer(f"🤺 <b>{message.from_user.full_name}</b> зарядил револьвер! Кто рискнет?", reply_markup=kb)

@dp.callback_query(F.data == "accept_duel")
async def process_duel(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    p1_id = active_duels.get(chat_id)
    p2_id = callback.from_user.id
    if not p1_id or p2_id == p1_id:
        return await callback.answer("Ошибка или это ваш вызов.")
    del active_duels[chat_id]
    await callback.message.edit_text("🔫 Барабан крутится...")
    await asyncio.sleep(2)
    loser_id = random.choice([p1_id, p2_id])
    try:
        await bot.restrict_chat_member(chat_id, loser_id, permissions=types.ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=5))
        await callback.message.answer(f"💥 БАБАХ! Игрок получил мут на 5 минут.")
    except:
        await callback.message.answer("🛡 Щелчок! Это был админ.")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 Бот S010lvloon готов!\n\n📜 #rules — правила\n🤺 /duel — дуэль\n🤖 /ai — ИИ")

async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
