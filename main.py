import logging
import asyncio
import random
from datetime import timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- TOKEN ----------------
BOT_TOKEN = "8104909560:AAHUS88zCrxDukxqMIOZBMIhVE3M3G4WjP8"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ---------------- DUELS STORAGE ----------------
active_duels = {}

# ---------------- RULES TEXT ----------------
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

# ---------------- LINKS ----------------
CHANNEL_URL = "https://t.me/+7Vf0p3jEjB9iMTUx"
CHAT_URL = "https://t.me/chat_S010lvloon"

# ---------------- RULES HANDLERS ----------------
@dp.message(lambda message: message.text and "#rules" in message.text.lower())
async def handle_rules_tag(message: Message):
    await message.reply(RULES_HTML, disable_web_page_preview=True)

@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.reply(RULES_HTML, disable_web_page_preview=True)

# ---------------- DUEL COMMAND ----------------
@dp.message(Command("duel"))
async def cmd_duel(message: Message):
    if message.chat.type == "private":
        return await message.reply("🎮 Дуэли проводятся только в группах!")

    chat_id = message.chat.id
    if chat_id in active_duels:
        return await message.reply("⚠️ Дуэль уже предложена! Дождитесь принятия.")

    active_duels[chat_id] = message.from_user.id

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Принять вызов! 🤝", callback_data="accept_duel")]
        ]
    )

    await message.answer(
        f"🤺 <b>{message.from_user.full_name}</b> зарядил револьвер! Кто готов рискнуть?",
        reply_markup=kb
    )

@dp.callback_query(F.data == "accept_duel")
async def process_duel(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    p1_id = active_duels.get(chat_id)
    p2_id = callback.from_user.id

    if not p1_id:
        return await callback.answer("Дуэль завершена.")
    if p2_id == p1_id:
        return await callback.answer("Стреляться с самим собой нельзя! 😅", show_alert=True)

    del active_duels[chat_id]

    await callback.message.edit_text(
        f"🔫 Барабан крутится... <b>{callback.from_user.full_name}</b> принял вызов!"
    )
    await asyncio.sleep(2)

    loser_id = random.choice([p1_id, p2_id])

    try:
        member = await bot.get_chat_member(chat_id, loser_id)
        loser_name = member.user.full_name

        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=loser_id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=5)
        )

        await callback.message.answer(
            f"💥 <b>БАБАХ!</b> {loser_name} словил маслину и умолк на 5 минут."
        )

    except Exception:
        await callback.message.answer("🛡 Щелчок! Удачливый админ выжил.")

# ---------------- START ----------------
@dp.message(Command("start"))
async def cmd_start(message: Message):

    # --- PRIVATE CHAT ---
    if message.chat.type == "private":
        text = """
<tg-emoji emoji-id="5197269100878907942">💎</tg-emoji> <b>Добро пожаловать!</b> <tg-emoji emoji-id="5197269100878907942">💎</tg-emoji>

<tg-emoji emoji-id="5352783059143901208">🤖</tg-emoji> Официальный бот проекта
<tg-emoji emoji-id="5424857974784925603">🛡</tg-emoji> Без фейков и накруток
<tg-emoji emoji-id="5877488510637706502">🔥</tg-emoji> Только живая аудитория

<tg-emoji emoji-id="5422789690333883156">👇</tg-emoji> <b>Для доступа вступи:</b>
"""

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📢 Вступить в канал", url=CHANNEL_URL)],
                [InlineKeyboardButton(text="💬 Вступить в чат", url=CHAT_URL)]
            ]
        )

        await message.answer(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    # --- GROUP/SUPERGROUP ---
    else:
        await message.reply(
            "🤖 Бот активен!\n\n"
            "📜 #rules — правила чата\n"
            "📜 /rules — правила чата\n"
            "🤺 /duel — вызвать на дуэль"
        )

# ---------------- MAIN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())