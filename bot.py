import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Отримання API ключів з змінних середовища
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Перевірка наявності необхідних API ключів
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
    raise ValueError("Валідний TELEGRAM_BOT_TOKEN не знайдено в змінних середовища. Будь ласка, додайте справжній токен у файл .env")

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    logging.warning("Валідний ANTHROPIC_API_KEY не знайдено в змінних середовища. Функціональність LLM буде недоступна.")

# Ініціалізація бота та диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Обробник команди /start
@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    """Обробник команди /start"""
    await message.answer(f"Привіт, {message.from_user.full_name}! Я Зірковий Помічник. Чим можу допомогти?")

# Обробник для всіх текстових повідомлень
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """Обробник для всіх текстових повідомлень"""
    await message.answer("Бот отримав ваше повідомлення. Скоро я навчуся відповідати на запитання про зірку!")

# Функція для запуску бота
async def main() -> None:
    """Головна функція для запуску бота"""
    # Видалення вебхуків у випадку їх наявності
    await bot.delete_webhook(drop_pending_updates=True)
    # Запуск поллінгу
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())