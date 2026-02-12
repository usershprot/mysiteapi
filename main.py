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

# Импортируем OpenAI для работы с OpenRouter
from openai import AsyncOpenAI

# --- 1. УПРАВЛЕНИЯ ДАННЫМИ ---

class BotStorage:
    @staticmethod
    def load_json(file_path: str, default: dict) -> dict:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
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
            "model": "qwen/qwen-2.5-coder-32b-instruct:free", # Рекомендуемое ID для Qwen 3 Coder на OpenRouter
            "prompt": "Ты — Джарвис, ироничный ассистент S010lvloon. Отвечай кратко.",
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

# --- 2. ЛОГИКА ИИ (OpenRouter) ---

class AIProcessor:
    def __init__(self, api_key: str, config: ConfigManager):
        # Настройка клиента под OpenRouter
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.config = config

    async def chat(self, messages: List[Dict]) -> Optional[str]:
        try:
            full_msgs = [{"role": "system", "content": self.config.get("prompt")}] + messages
            response = await self.client.chat.completions.create(
                model=self.config.get("model"),
                messages=full_msgs
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return f"Ошибка ИИ: {e}"

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
        "<b>🤖 Привет! Я Джарвис (OpenRouter Edition).</b>\n\n"
        "🔹 <b>ИИ Чат:</b> Напиши: <i>Джарвис, код на Python?</i>\n"
        "🔹 <b>Бизнес-режим:</b> Редактирую твои сообщения в личке.\n"
        "🔹 <b>Дуэль:</b> /duel в группах."
    )
    await msg.answer(welcome_text)

@router.business_message(F.text.regexp(AI_TRIGGER))
@router.message(F.text.regexp(AI_TRIGGER))
async def ai_handler(msg: Message, ai: AIProcessor, history: HistoryManager, config: ConfigManager):
    user_key = f"{msg.chat.id}_{msg.from_user.id}"
    query = re.sub(AI_TRIGGER, "", msg.text, flags=re.IGNORECASE).strip()
    if not query: return

    if not msg.business_connection_id:
        await msg.bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

    history.add_msg(user_key, "user", query, config.get("context_size"))
    response = await ai.chat(history.get_history(user_key))

    if response:
        history.add_msg(user_key, "assistant", response, config.get("context_size"))
        clean_res = response.replace("<", "&lt;").replace(">", "&gt;")[:3500]
        final_text = f"<blockquote>💻 {msg.text[:200]}</blockquote>\n<blockquote>🤖 {clean_res}</blockquote>"

        if msg.business_connection_id:
            await msg.bot.edit_message_text(
                business_connection_id=msg.business_connection_id,
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                text=final_text
            )
        else:
            await msg.reply(final_text)

# (Остальные обработчики дуэли и админки остаются без изменений...)
@router.message(Command("rules"))
@router.message(lambda m: m.text and "#rules" in m.text.lower())
async def rules_handler(msg: Message, config: ConfigManager):
    await msg.answer(config.get("rules"), disable_web_page_preview=True)

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
        return await call.answer("Нельзя играть с собой!", show_alert=True)
    
    await call.message.edit_text("🔫 Барабан крутится...")
    await asyncio.sleep(2)
    
    loser = random.choice([challenger_id, call.from_user.id])
    try:
        await call.message.bot.restrict_chat_member(
            call.message.chat.id, loser, 
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=5)
        )
        await call.message.answer(f"💥 БАБАХ! Мут на 5 минут.")
    except:
        await call.message.answer("🛡 Осечка (админский щит)!")

@router.message(Command("S2HFHF"))
async def admin_start(msg: Message, state: FSMContext):
    await msg.answer("🔑 Пароль:")
    await state.set_state(AdminStates.waiting_auth)

@router.message(AdminStates.waiting_auth)
async def admin_auth(msg: Message, state: FSMContext):
    if msg.text == os.getenv("ADMIN_PASSWORD", "import"):
        await state.set_state(AdminStates.menu)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Промт", callback_data="set_prompt")],
            [InlineKeyboardButton(text="📜 Правила", callback_data="set_rules")],
            [InlineKeyboardButton(text="❌ Выход", callback_data="exit")]
        ])
        await msg.answer("⚙️ Панель Джарвиса:", reply_markup=kb)
    else:
        await msg.answer("❌ Доступ закрыт.")
        await state.clear()

@router.callback_query(F.data == "set_prompt", AdminStates.menu)
async def edit_p(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи новый системный промт:")
    await state.set_state(AdminStates.editing_prompt)

@router.callback_query(F.data == "set_rules", AdminStates.menu)
async def edit_r(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи новый HTML для правил:")
    await state.set_state(AdminStates.editing_rules)

@router.message(AdminStates.editing_prompt)
@router.message(AdminStates.editing_rules)
async def admin_save(msg: Message, state: FSMContext, config: ConfigManager):
    curr = await state.get_state()
    key = "prompt" if curr == AdminStates.editing_prompt else "rules"
    config.set(key, msg.text)
    await msg.answer("✅ Сохранено!")
    await state.set_state(AdminStates.menu)

@router.callback_query(F.data == "exit")
async def exit_adm(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()

# --- 5. ЗАПУСК ---

async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    # Можно заменить прямо здесь или через .env
    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "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")
    
    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    
    cfg = ConfigManager()
    hist = HistoryManager()
    ai = AIProcessor(api_key=OPENROUTER_KEY, config=cfg)

    dp.include_router(router)
    await dp.start_polling(bot, config=cfg, history=hist, ai=ai)

if __name__ == "__main__":
    asyncio.run(main())