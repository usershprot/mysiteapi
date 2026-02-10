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

# Дефолтные настройки
default_config = {
    "model": "open-mistral-7b",
    "prompt": "Ты — полезный и ироничный ассистент в Telegram-чате S010lvloon. Отвечай кратко.",
    "rules": "Правила чата: без спама, без мата."
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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

# --- АДМИН ПАНЕЛЬ (/S2HFHF) ---

@dp.message(Command("S2HFHF"))
async def admin_auth(message: Message, state: FSMContext):
    await message.answer("🔒 Введите пароль доступа:")
    await state.set_state(AdminStates.waiting_for_password)

@dp.message(AdminStates.waiting_for_password)
async def check_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await state.set_state(AdminStates.main_menu)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Изменить Промт", callback_data="edit_prompt")],
            [InlineKeyboardButton(text="📜 Изменить Правила", callback_data="edit_rules")],
            [InlineKeyboardButton(text="🤖 Изменить Модель", callback_data="edit_model")],
            [InlineKeyboardButton(text="❌ Выход", callback_data="exit_admin")]
        ])
        await message.answer(f"⚙️ <b>S010lvloon Admin</b>\nТекущая модель: <code>{config['model']}</code>", reply_markup=kb)
    else:
        await message.answer("❌ Доступ запрещен.")
        await state.clear()

@dp.callback_query(F.data == "edit_prompt", AdminStates.main_menu)
async def start_edit_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.answer(f"Текущий промт:\n<code>{config['prompt']}</code>\n\nПришли новый текст:")
    await state.set_state(AdminStates.editing_prompt)

@dp.message(AdminStates.editing_prompt)
async def save_prompt_logic(message: Message, state: FSMContext):
    config['prompt'] = message.text
    save_config(config)
    await message.answer("✅ Промт сохранен в JSON!")
    await state.set_state(AdminStates.main_menu)

@dp.callback_query(F.data == "edit_rules", AdminStates.main_menu)
async def start_edit_rules(call: CallbackQuery, state: FSMContext):
    await call.message.answer(f"Текущие правила:\n{config['rules']}\n\nПришли новый текст правил:")
    await state.set_state(AdminStates.editing_rules)

@dp.message(AdminStates.editing_rules)
async def save_rules_logic(message: Message, state: FSMContext):
    config['rules'] = message.text
    save_config(config)
    await message.answer("✅ Правила обновлены!")
    await state.set_state(AdminStates.main_menu)

@dp.callback_query(F.data == "edit_model", AdminStates.main_menu)
async def menu_model(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="open-mistral-7b (Дешево)", callback_data="set_m_open-mistral-7b")],
        [InlineKeyboardButton(text="mistral-small-latest", callback_data="set_m_mistral-small-latest")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_admin")]
    ])
    await call.message.edit_text("Выберите модель Mistral:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_m_"))
async def save_model_logic(call: CallbackQuery):
    new_model = call.data.replace("set_m_", "")
    config['model'] = new_model
    save_config(config)
    await call.answer(f"Модель {new_model} активирована!", show_alert=True)
    await exit_admin(call, None) # Перезапуск меню

@dp.callback_query(F.data == "exit_admin")
async def exit_admin(call: CallbackQuery, state: FSMContext):
    if state: await state.clear()
    await call.message.edit_text("🚪 Сессия закрыта.")

# --- ОСНОВНЫЕ ФУНКЦИИ ---

@dp.message(Command("ai"))
async def cmd_ai(message: Message):
    user_id = message.from_user.id
    if user_id in user_cooldowns and time() - user_cooldowns[user_id] < 15:
        return await message.reply("⏳ Не спамь.")
    
    prompt = message.text.replace("/ai", "").strip()
    if not prompt: return await message.reply("Напиши вопрос.")

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
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.answer(config['rules'], disable_web_page_preview=True)

@dp.message(lambda m: m.text and "#rules" in m.text.lower())
async def tag_rules(message: Message):
    await message.reply(config['rules'], disable_web_page_preview=True)

# (Функция дуэли /duel остается прежней)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
