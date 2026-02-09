import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from datetime import timedelta

# Библиотека для Mistral
from mistralai import Mistral

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ТОКЕНЫ
BOT_TOKEN = "8104909560:AAHUS88zCrxDukxqMIOZBMIhVE3M3G4WjP8"
MISTRAL_API_KEY = "Fl1fzomHyW03LF4LePSmwJnJTht0XKsl" 

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

# Словарь для активных дуэлей
active_duels = {}

# Текст правил
RULES_HTML = """<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> <b>Правила чата</b>
<tg-emoji emoji-id="5424857974784925603">🚫</tg-emoji> Без спама и рекламы
<tg-emoji emoji-id="4916086774649848789">🔗</tg-emoji> Без ссылок без разрешения админа
<tg-emoji emoji-id="5352783059143901208">🖕</tg-emoji> Без оскорблений
<tg-emoji emoji-id="5877488510637706502">🚫</tg-emoji> Запрещены мошеннические схемы
<tg-emoji emoji-id="5318912942752669674">💻</tg-emoji> Запрещено просить взломать что либо
<tg-emoji emoji-id="5422789690333883156">ℹ️</tg-emoji> Запрещено писать не по делу, (просить инструменты для DOX\\OSINT)
<tg-emoji emoji-id="5258500400918587241">✍️</tg-emoji> Запрещено разговаривать на других языках кроме RU/ENG
<tg-emoji emoji-id="5206432422194849059">🔒</tg-emoji> Нарушение = мут / бан

А кто не согласен с правилами читать <a href="https://hhroot.alwaysdata.net/">здесь</a>"""

# --- РЕЖИМ ИИ (Mistral) ---

@dp.message(Command("ai"))
async def cmd_ai(message: Message):
    prompt = message.text.replace("/ai", "").strip()
    
    if not prompt:
        return await message.reply("Введите запрос, например: <code>/ai привет!</code>")

    # Эффект "печатает"
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Запрос к Mistral Medium Latest
        chat_response = await asyncio.to_thread(
            mistral_client.chat.complete,
            model="mistral-medium-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = chat_response.choices[0].message.content
        
        # Если текст слишком длинный, обрезаем его для Telegram
        if len(response_text) > 4000:
            response_text = response_text[:4000] + "..."
            
        await message.reply(response_text, parse_mode=None)
    except Exception as e:
        logger.error(f"Mistral Error: {e}")
        await message.reply("❌ Не удалось получить ответ от Mistral AI.")

# --- ПРАВИЛА ---

@dp.message(lambda message: message.text and "#rules" in message.text.lower())
async def handle_rules_tag(message: Message):
    await message.reply(RULES_HTML, disable_web_page_preview=True)

@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.reply(RULES_HTML, disable_web_page_preview=True)

# --- ДУЭЛЬ ---

@dp.message(Command("duel"))
async def cmd_duel(message: Message):
    if message.chat.type == "private":
        return await message.reply("🎮 Дуэли только в группах!")
    
    active_duels[message.chat.id] = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Принять вызов! 🤝", callback_data="accept_duel")
    ]])
    await message.answer(f"🤺 <b>{message.from_user.full_name}</b> вызывает на дуэль!", reply_markup=kb)

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
        await bot.restrict_chat_member(
            chat_id, loser_id, 
            permissions=types.ChatPermissions(can_send_messages=False), 
            until_date=timedelta(minutes=5)
        )
        await callback.message.answer(f"💥 БАБАХ! Игрок получил мут на 5 минут.")
    except:
        await callback.message.answer("🛡 Щелчок! Это был админ.")

# --- СТАРТ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 Бот готов!\n\n📜 #rules — правила\n🤺 /duel — дуэль\n🤖 /ai [запрос] — ИИ Mistral")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
