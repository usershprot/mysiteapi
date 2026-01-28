import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8566538172:AAHFTXxjJ43lvZgRgxzLIuXIWRpS-tEW_WI'

RULES_TEXT = """📜 Правила чата
1. Без спама и рекламы
2. Без ссылок без разрешения админа
3. Без оскорблений
4. Запрещены мошеннические схемы
5. Запрещено просить взломать что либо

🔒 Нарушение = мут / бан"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот-триггер. Если вы напишете сообщение с хэштегом #rules, "
        "я отправлю полные правила группы. Также я реагирую на ключевые слова."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text if message.text else ""
    
    # Проверяем, содержит ли сообщение хэштег #rules
    if "#rules" in text.lower()
        await message.reply_text(RULES_TEXT)
        logger.info(f"Отправлены правила пользователю {message.from_user.id}")
    
    # Также можно добавить проверку на ключевые слова (опционально)
    elif any(keyword in text.lower() for keyword in ["правила", "rules", "правила группы"]):
        await message.reply_text("📋 Кажется, вы спрашиваете про правила? Добавьте #rules в сообщение, чтобы получить полный список!")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rules", rules_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
