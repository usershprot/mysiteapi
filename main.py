import asyncio
import os
import yt_dlp
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode, ChatAction

# --- НАСТРОЙКИ ---
BOT_TOKEN = "7855914162:AAHJRP23ZcO-IfLAB-qMOeEhbFPupyXnUFo"
BOT_NAME = "S010lvloonSave_bot"
DOWNLOAD_DIR = "downloads"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройки yt-dlp
YDL_OPTIONS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome = (
        f"🤖 <b>Добро пожаловать в {BOT_NAME}!</b>\n\n"
        "Я помогу тебе сохранить контент из соцсетей.\n"
        "🎬 <b>Просто отправь мне ссылку на:</b>\n"
        "• YouTube / Shorts\n"
        "• Instagram Reels / Posts\n"
        "• TikTok (без водяных знаков)\n"
        "• VK / Twitter / Likee\n\n"
        "<i>Используй /info для подробностей.</i>"
    )
    await message.answer(welcome, parse_mode=ParseMode.HTML)

@dp.message(Command("info"))
async def cmd_info(message: Message):
    info_text = (
        f"ℹ️ <b>Информация о боте {BOT_NAME}</b>\n\n"
        "<b>Технологии:</b> AIogram 3.x + YT-DLP\n"
        "<b>Лимиты:</b> Видео до 50 МБ (ограничение Telegram API).\n\n"
        "Если видео не скачивается, возможно оно:\n"
        "1. Приватное (нужны куки).\n"
        "2. Слишком длинное (стрим).\n"
        "3. Платформа временно заблокировала доступ."
    )
    await message.answer(info_text, parse_mode=ParseMode.HTML)

@dp.message(F.text.contains("http"))
async def download_handler(message: Message):
    # Извлекаем ссылку
    url = re_search_url(message.text)
    if not url:
        return

    status = await message.answer("⏳ <b>Анализирую ссылку...</b>", parse_mode=ParseMode.HTML)
    
    # Показываем, что бот «записывает видео» (красивый статус в шапке чата)
    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)

    try:
        loop = asyncio.get_event_loop()
        
        def download_sync():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')

        # Скачиваем в отдельном потоке
        file_path, title = await loop.run_in_executor(None, download_sync)
        
        if os.path.exists(file_path):
            # Проверка размера файла (50MB лимит)
            filesize = os.path.getsize(file_path) / (1024 * 1024)
            
            if filesize > 50:
                await status.edit_text(f"⚠️ <b>Файл слишком большой:</b> {filesize:.1f} МБ\n"
                                       "Телеграм разрешает отправлять ботам файлы только до 50 МБ.")
                os.remove(file_path)
                return

            video = FSInputFile(file_path)
            await message.reply_video(video, caption=f"✅ <b>{title}</b>\n\n📥 Сохранено через @{BOT_NAME}", parse_mode=ParseMode.HTML)
            await status.delete()
            os.remove(file_path)
        else:
            await status.edit_text("❌ Ошибка: Не удалось создать файл.")

    except Exception as e:
        await status.edit_text(f"❌ <b>Ошибка при загрузке:</b>\n<code>{str(e)[:150]}</code>", parse_mode=ParseMode.HTML)

def re_search_url(text):
    import re
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

# --- ЗАПУСК ---

async def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    print(f"Бот {BOT_NAME} запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
