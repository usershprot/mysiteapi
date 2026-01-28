import asyncio
from aiogram import Bot, Dispatcher, types, F

# Вставь сюда свой токен
TOKEN = 'ВАШ_ТОКЕН'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик сообщений, содержащих #rules
@dp.message(F.text.lower.contains("#rules"))
async def send_rules(message: types.Message):
    rules_text = (
        "📜 **Правила чата**\n\n"
        "1. Без спама и рекламы\n"
        "2. Без ссылок без разрешения админа\n"
        "3. Без оскорблений\n"
        "4. Запрещены мошеннические схемы\n\n"
        "🔒 **Нарушение = мут / бан**"
    )
    
    # Отвечаем на сообщение пользователя
    await message.reply(rules_text, parse_mode="Markdown")

async def main():
    print("Бот запущен. Жду команду #rules...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
