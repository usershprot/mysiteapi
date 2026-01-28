import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # ДВОЙНОЕ подчеркивание с обеих сторон!

# Токен вашего бота (ВСТАВЬТЕ НОВЫЙ ТОКЕН ЗДЕСЬ!)
BOT_TOKEN = "8104909560:AAHUS88zCrxDukxqMIOZBMIhVE3M3G4WjP8"

# Инициализация бота для aiogram 3.7.0+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Текст правил в HTML формате с эмодзи
RULES_HTML = """<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Правила чата
<tg-emoji emoji-id="5424857974784925603">🚫</tg-emoji> Без спама и рекламы
<tg-emoji emoji-id="4916086774649848789">🔗</tg-emoji> Без ссылок без разрешения админа
<tg-emoji emoji-id="5352783059143901208">🖕</tg-emoji> Без оскорблений
<tg-emoji emoji-id="5877488510637706502">🚫</tg-emoji> Запрещены мошеннические схемы
<tg-emoji emoji-id="5318912942752669674">💻</tg-emoji> Запрещено просить взломать что либо
<tg-emoji emoji-id="5422789690333883156">ℹ️</tg-emoji> Запрещено писать не по делу, (просить инструменты для DOX\\OSINT)
<tg-emoji emoji-id="5206432422194849059">🔒</tg-emoji> Нарушение = мут / бан"""

# Обработчик для #rules
@dp.message(lambda message: message.text and "#rules" in message.text.lower())
async def handle_rules(message: Message):
    try:
        # Отправляем с HTML эмодзи
        await message.reply(RULES_HTML)
        logger.info(f"Отправлены правила в чате: {message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")
        # Fallback на обычный текст
        fallback_text = """✍️ Правила чата
🚫 Без спама и рекламы
🔗 Без ссылок без разрешения админа
🖕 Без оскорблений
🚫 Запрещены мошеннические схемы
💻 Запрещено просить взломать что либо
ℹ️ Запрещено писать не по делу, (просить инструменты для DOX\\OSINT)
🔒 Нарушение = мут / бан"""
        await message.reply(fallback_text)

# Команда для ручной отправки правил
@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    await handle_rules(message)

# Команда для проверки бота
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 Бот работает! Отправьте #rules для получения правил")

# Основная функция
async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())