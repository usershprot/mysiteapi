import logging
import asyncio
import random
import json
import os
import re
from datetime import timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем Cerebras
from cerebras.cloud.sdk import Cerebras

# --- 1. УПРАВЛЕНИЯ ДАННЫМИ ---
class BotStorage:
    @staticmethod
    def load_json(file_path: str, default: dict) -> dict:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    @staticmethod
    def save_json(file_path: str, data: dict):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

class ConfigManager:
    def __init__(self, path="config.json"):
        self.path = path
        self.data = BotStorage.load_json(path, {
            "model": "llama-3.3-70b", 
            "prompt": "Ты — Джарвис, ироничный ассистент. Отвечай кратко и на русском.",
            "rules": "Правила не установлены.",
            "context_size": 10
        })

    def get(self, key): return self.data.get(key)
    def set(self, key, value):
        self.data[key] = value
        BotStorage.save_json(self.path, self.data)

class HistoryManager:
    def __init__(self, path="history.json"):
        self.path = path
        self.data = BotStorage.load_json(path, {})

    def add_msg(self, key: str, role: str, content: str, limit: int):
        if key not in self.data: self.data[key] = []
        self.data[key].append({"role": role, "content": content})
        self.data[key] = self.data[key][-limit:]
        BotStorage.save_json(self.path, self.data)

    def get_history(self, key: str): return self.data.get(key, [])

# --- 2. ЛОГИКА ИИ (Cerebras) ---
class AIProcessor:
    def __init__(self, api_key: str, config: ConfigManager):
        self.client = Cerebras(api_key=api_key)
        self.config = config

    async def chat(self, messages: List[Dict]) -> Optional[str]:
        try:
            # Запускаем синхронный вызов Cerebras в отдельном потоке, чтобы не блокировать бот
            loop = asyncio.get_event_loop()
            full_msgs = [{"role": "system", "content": self.config.get("prompt")}] + messages
            
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat.completions.create(
                    model=self.config.get("model"),
                    messages=full_msgs
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Cerebras AI Error: {e}")
            return f"⚠️ Ошибка ИИ: {e}"

# --- 3. СОСТОЯНИЯ FSM ---
class AdminStates(StatesGroup):
    waiting_auth = State()
    menu = State()
    editing_prompt = State()
    editing_rules = State()

# --- 4. ОБРАБОТЧИКИ ---
router = Router()
AI_TRIGGER = r"(?i)^(/ai|джарвис|sai|s2)\b"

@router.message(Command("start"))
async def start_handler(msg: Message):
    welcome_text = (
        "<b>🤖 Привет! Я Джарвис (Cerebras Powered).</b>\n\n"
        "🔹 <b>ИИ Чат:</b> Напиши: <i>Джарвис, как дела?</i>\n"
        "🔹 <b>Бизнес-режим:</b> Работает в личке.\n"
        "🔹 <b>Дуэль:</b> /duel в группах."
    )
    await msg.answer(welcome_text)

@router.message(F.text.regexp(AI_TRIGGER))
async def ai_handler(msg: Message, ai: AIProcessor, history: HistoryManager, config: ConfigManager):
    user_key = f"{msg.chat.id}_{msg.from_user.id}"
    query = re.sub(AI_TRIGGER, "", msg.text, flags=re.IGNORECASE).strip()
    if not query: return

    # Эффект "печатает"
    await msg.bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

    history.add_msg(user_key, "user", query, config.get("context_size"))
    response = await ai.chat(history.get_history(user_key))

    if response:
        history.add_msg(user_key, "assistant", response, config.get("context_size"))
        # Экранируем HTML символы
        clean_res = response.replace("<", "&lt;").replace(">", "&gt;")[:3500]
        final_text = f"💻 <b>Вопрос:</b> {query[:100]}...\n\n🤖 <b>Джарвис:</b>\n{clean_res}"
        await msg.reply(final_text)

# --- 5. ДУЭЛЬ И АДМИНКА ---
@router.message(Command("duel"))
async def duel_handler(msg: Message):
    if msg.chat.type == "private": return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Принять вызов! 🤝", callback_data=f"duel_{msg.from_user.id}")
    ]])
    await msg.answer(f"🤺 <b>{msg.from_user.first_name}</b> вызывает на дуэль!", reply_markup=kb)

@router.callback_query(F.data.startswith("duel_"))
async def duel_callback(call: CallbackQuery):
    challenger_id = int(call.data.split("_")[1])
    if call.from_user.id == challenger_id:
        return await call.answer("Нельзя стреляться с собой!", show_alert=True)
    
    await call.message.edit_text("🔫 Барабан крутится...")
    await asyncio.sleep(1.5)
    
    loser = random.choice([challenger_id, call.from_user.id])
    try:
        await call.message.bot.restrict_chat_member(
            call.message.chat.id, loser, 
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=5)
        )
        await call.message.answer(f"💥 БАБАХ! Один готов. Мут на 5 минут.")
    except Exception:
        await call.message.answer("🛡 Осечка! (У игрока иммунитет/админка)")

# Пароль для входа: S2HFHF
@router.message(Command("S2HFHF"))
async def admin_start(msg: Message, state: FSMContext):
    await msg.answer("🔑 Введите секретный код:")
    await state.set_state(AdminStates.waiting_auth)

@router.message(AdminStates.waiting_auth)
async def admin_auth(msg: Message, state: FSMContext):
    if msg.text == os.getenv("ADMIN_PASSWORD", "admin123"):
        await state.set_state(AdminStates.menu)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Изменить Промт", callback_data="set_prompt")],
            [InlineKeyboardButton(text="❌ Выход", callback_data="exit")]
        ])
        await msg.answer("⚙️ Настройки ИИ:", reply_markup=kb)
    else:
        await msg.answer("❌ Доступ закрыт.")
        await state.clear()

@router.callback_query(F.data == "exit")
async def exit_adm(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()

# --- 6. ЗАПУСК ---
async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    # API Ключи
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    
    cfg = ConfigManager()
    hist = HistoryManager()
    ai = AIProcessor(api_key=CEREBRAS_KEY, config=cfg)

    dp.include_router(router)
    
    print("🚀 Бот запущен!")
    await dp.start_polling(bot, config=cfg, history=hist, ai=ai)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")