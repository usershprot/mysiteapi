import logging
import asyncio
import random
import os
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

from openai import OpenAI

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- TOKENS ----------------
BOT_TOKEN = "8104909560:AAHUS88zCrxDukxqMIOZBMIhVE3M3G4WjP8"
OPENROUTER_API_KEY = "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"

# ---------------- OPENROUTER CLIENT ----------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# ---------------- BOT ----------------
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ---------------- STORAGE ----------------
active_duels = {}
ttt_games = {}

# ---------------- RULES (ORIGINAL) ----------------
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

# ---------------- TTT LOGIC ----------------
WIN_COMBOS = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6)
]

def check_winner(board, s):
    return any(all(board[i] == s for i in c) for c in WIN_COMBOS)

def draw(board):
    return all(x != " " for x in board)

def board_kb(board, gid):
    kb = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            row.append(
                InlineKeyboardButton(
                    text=board[i] if board[i] != " " else "➖",
                    callback_data=f"ttt:{gid}:{i}"
                )
            )
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ---------------- OPENROUTER AI MOVE ----------------
async def ai_move_openrouter(board):
    prompt = (
        "Ты играешь в крестики-нолики за ⭕.\n"
        "Поле:\n"
        "0 1 2\n"
        "3 4 5\n"
        "6 7 8\n\n"
        f"Текущее состояние: {board}\n"
        "Ответь ТОЛЬКО цифрой (0-8)."
    )

    completion = await asyncio.to_thread(
        client.chat.completions.create,
        model="deepseek/deepseek-r1-0528:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3,
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "https://yourbot.local",
            "X-Title": "TicTacToeBot"
        }
    )

    text = completion.choices[0].message.content
    digits = [int(c) for c in text if c.isdigit()]
    valid = [i for i,v in enumerate(board) if v == " "]
    return digits[0] if digits and digits[0] in valid else random.choice(valid)

# ---------------- RULES HANDLERS ----------------
@dp.message(Command("rules"))
async def rules(message: Message):
    await message.reply(RULES_HTML, disable_web_page_preview=True)

# ---------------- /DUEL ----------------
@dp.message(Command("duel"))
async def duel(message: Message):
    if message.chat.type == "private":
        return await message.reply("🎮 Дуэли только в группах")

    chat_id = message.chat.id
    if chat_id in active_duels:
        return await message.reply("⚠️ Дуэль уже активна")

    active_duels[chat_id] = message.from_user.id
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Принять 🤝", callback_data="accept_duel")]]
    )

    await message.answer(
        f"🤺 <b>{message.from_user.full_name}</b> зарядил револьвер!",
        reply_markup=kb
    )

@dp.callback_query(F.data == "accept_duel")
async def accept_duel(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    p1 = active_duels.get(chat_id)
    p2 = cb.from_user.id

    if not p1 or p1 == p2:
        return await cb.answer("Ошибка", show_alert=True)

    del active_duels[chat_id]
    loser = random.choice([p1, p2])

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=loser,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=5)
        )
        await cb.message.answer("💥 БАБАХ! Один выбыл на 5 минут")
    except:
        await cb.message.answer("🛡 Админ выжил")

# ---------------- /TDUEL ----------------
@dp.message(Command("tduel"))
async def tduel(message: Message):
    if message.chat.type == "private":
        return await message.reply("⚔️ Только в группе")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Принять ❌⭕", callback_data="tduel_accept")]]
    )

    await message.answer(
        f"🎮 <b>{message.from_user.full_name}</b> вызывает в крестики-нолики!",
        reply_markup=kb
    )

@dp.callback_query(F.data == "tduel_accept")
async def tduel_accept(cb: CallbackQuery):
    p1 = cb.message.from_user
    p2 = cb.from_user
    board = [" "] * 9
    gid = cb.message.message_id

    ttt_games[gid] = {
        "board": board,
        "players": [p1.id, p2.id],
        "turn": p1.id,
        "symbols": {p1.id: "❌", p2.id: "⭕"},
        "ai": False
    }

    await cb.message.edit_text(
        f"❌ {p1.full_name}\n⭕ {p2.full_name}\n\nХод ❌",
        reply_markup=board_kb(board, gid)
    )

# ---------------- /TTT AI ----------------
@dp.message(Command("ttt"))
async def ttt_ai(message: Message):
    board = [" "] * 9
    gid = message.message_id

    ttt_games[gid] = {
        "board": board,
        "player": message.from_user.id,
        "ai": True
    }

    await message.answer(
        "🤖 Игра против ИИ\nТы — ❌",
        reply_markup=board_kb(board, gid)
    )

# ---------------- TTT CALLBACK ----------------
@dp.callback_query(F.data.startswith("ttt:"))
async def ttt_cb(cb: CallbackQuery):
    _, gid, idx = cb.data.split(":")
    gid, idx = int(gid), int(idx)

    game = ttt_games.get(gid)
    if not game:
        return await cb.answer("Игра окончена")

    board = game["board"]
    if board[idx] != " ":
        return await cb.answer("Занято")

    board[idx] = "❌"

    if check_winner(board, "❌"):
        await cb.message.edit_text("🎉 Ты победил!")
        del ttt_games[gid]
        return

    if draw(board):
        await cb.message.edit_text("🤝 Ничья")
        del ttt_games[gid]
        return

    ai_idx = await ai_move_openrouter(board)
    board[ai_idx] = "⭕"

    if check_winner(board, "⭕"):
        await cb.message.edit_text("🤖 ИИ победил")
        del ttt_games[gid]
        return

    await cb.message.edit_reply_markup(reply_markup=board_kb(board, gid))

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.reply(
        "🤖 Бот активен\n"
        "/rules — правила\n"
        "/duel — дуэль\n"
        "/tduel — крестики с другом\n"
        "/ttt — крестики с ИИ"
    )

# ---------------- MAIN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())