import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from translations import translation_manager
from knowledge_utils import read_knowledge_base, find_relevant_context
from llm_utils import generate_response

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Отримання API ключів з змінних середовища з відладочним виводом
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print(
    f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}"
)  # Для відладки, видаліть після перевірки

if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
    raise ValueError(
        "Валідний TELEGRAM_BOT_TOKEN не знайдено в змінних середовища. Будь ласка, додайте справжній токен у файл .env"
    )

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    logging.warning(
        "Валідний ANTHROPIC_API_KEY не знайдено в змінних середовища. Функціональність LLM буде недоступна."
    )

# Ініціалізація бота та диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Словник для зберігання мовних налаштувань користувачів
user_languages = {}


# Функція для отримання мови користувача
def get_user_language(user_id: int) -> str:
    """Отримання мови користувача

    Args:
        user_id: ID користувача

    Returns:
        Код мови користувача
    """
    return user_languages.get(user_id, "en")


# Функція для створення головної клавіатури
def get_main_keyboard(language: str) -> InlineKeyboardMarkup:
    """Створення головної інлайн-клавіатури

    Args:
        language: Код мови

    Returns:
        Інлайн-клавіатура з кнопками
    """
    builder = InlineKeyboardBuilder()

    # Додаємо кнопки FAQ та Info
    builder.add(
        InlineKeyboardButton(
            text=translation_manager.get_text("button_faq", language),
            callback_data="faq",
        ),
        InlineKeyboardButton(
            text=translation_manager.get_text("button_info", language),
            callback_data="info",
        ),
    )

    # Додаємо кнопки перемикання мови
    builder.row(
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇲🇾 Bahasa Melayu", callback_data="lang_ms"),
    )

    return builder.as_markup()


# Функція для створення клавіатури повернення
def get_back_keyboard(language: str) -> InlineKeyboardMarkup:
    """Створення клавіатури з кнопкою повернення

    Args:
        language: Код мови

    Returns:
        Інлайн-клавіатура з кнопкою повернення
    """
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=translation_manager.get_text("button_back", language),
            callback_data="back",
        )
    )
    return builder.as_markup()


# Обробник команди /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обробник команди /start"""
    user_id = message.from_user.id
    language = get_user_language(user_id)

    welcome_text = translation_manager.get_text(
        "welcome_message", language, user_name=message.from_user.full_name
    )

    await message.answer(text=welcome_text, reply_markup=get_main_keyboard(language))


# Обробник команди /faq
@dp.message(Command("faq"))
async def command_faq_handler(message: Message) -> None:
    """Обробник команди /faq"""
    user_id = message.from_user.id
    language = get_user_language(user_id)

    faq_text = translation_manager.get_text("faq_text", language)

    await message.answer(
        text=faq_text, reply_markup=get_back_keyboard(language), parse_mode="Markdown"
    )


# Обробник команди /info
@dp.message(Command("info"))
async def command_info_handler(message: Message) -> None:
    """Обробник команди /info"""
    user_id = message.from_user.id
    language = get_user_language(user_id)

    info_text = translation_manager.get_text("info_text", language)

    await message.answer(
        text=info_text, reply_markup=get_back_keyboard(language), parse_mode="Markdown"
    )


# Обробник callback-запитів
@dp.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    """Обробник callback-запитів від інлайн-кнопок"""
    user_id = callback.from_user.id
    language = get_user_language(user_id)

    # Обробка запитів зміни мови
    if callback.data.startswith("lang_"):
        # Get the selected language from the callback data
        selected_lang = callback.data.split('_')[1]
        
        # Check if the language has actually changed
        current_lang = get_user_language(user_id)
        if selected_lang == current_lang:
            await callback.answer(translation_manager.get_text('language_already_selected', current_lang))
            return
            
        # Update the user's language preference
        user_languages[user_id] = selected_lang
        
        # Get the new text for the message
        welcome_text = translation_manager.get_text("welcome_message", selected_lang, user_name=callback.from_user.full_name)
        
        # Edit the message with the new language
        await callback.message.edit_text(
            text=welcome_text,
            reply_markup=get_main_keyboard(selected_lang)
        )

    # Обробка запиту FAQ
    elif callback.data == "faq":
        faq_text = translation_manager.get_text("faq_text", language)

        await callback.message.edit_text(
            text=faq_text,
            reply_markup=get_back_keyboard(language),
            parse_mode="Markdown",
        )

    # Обробка запиту Info
    elif callback.data == "info":
        info_text = translation_manager.get_text("info_text", language)

        await callback.message.edit_text(
            text=info_text,
            reply_markup=get_back_keyboard(language),
            parse_mode="Markdown",
        )

    # Обробка запиту повернення до головного меню
    elif callback.data == "back":
        welcome_text = translation_manager.get_text(
            "welcome_message", language, user_name=callback.from_user.full_name
        )

        await callback.message.edit_text(
            text=welcome_text, reply_markup=get_main_keyboard(language)
        )

    # Відповідь на callback-запит, щоб прибрати годинник завантаження
    await callback.answer()


# Функція для читання інструкцій персони
def read_persona_instructions(file_path: str = "persona_instructions.txt") -> str:
    """Читає інструкції щодо стилю спілкування зірки з файлу
    
    Args:
        file_path: Шлях до файлу з інструкціями
        
    Returns:
        Текст інструкцій або порожній рядок, якщо файл не знайдено
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"Помилка: Файл інструкцій персони '{file_path}' не знайдено.")
        return ""
    except Exception as e:
        logging.error(f"Помилка при читанні файлу інструкцій персони: {e}")
        return ""


# Обробник для всіх текстових повідомлень
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """Обробник для всіх текстових повідомлень"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    # Отримуємо текст запиту користувача
    query = message.text
    logging.info(f"Отримано запит від користувача {user_id}: {query}")
    
    # Надсилаємо індикатор набору тексту, щоб користувач знав, що бот обробляє запит
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Читаємо базу знань
        logging.info("Читаємо базу знань...")
        knowledge_text = read_knowledge_base("knowledge_base.txt")
        
        if not knowledge_text:
            # Якщо база знань недоступна
            logging.error("База знань недоступна або порожня")
            await message.answer(
                translation_manager.get_text("knowledge_base_error", language)
            )
            return
        
        # Шукаємо релевантний контекст
        logging.info("Пошук релевантного контексту...")
        relevant_context = find_relevant_context(query, knowledge_text, max_tokens=1000)
        
        if not relevant_context:
            # Якщо релевантна інформація не знайдена
            logging.info(f"Релевантний контекст не знайдено для запиту: {query}")
            await message.answer(
                translation_manager.get_text("no_relevant_info", language)
            )
            return
        
        # Читаємо інструкції персони
        logging.info("Читаємо інструкції персони...")
        persona_instructions = read_persona_instructions()
        if not persona_instructions:
            logging.warning("Файл інструкцій персони не знайдено. Використовуємо базові інструкції.")
            persona_instructions = "Ти - віртуальний помічник зірки. Відповідай дружньо та інформативно."
        
        # Генеруємо відповідь за допомогою LLM
        logging.info("Генеруємо відповідь за допомогою LLM...")
        llm_response = await generate_response(
            query=query,
            context=relevant_context,
            persona_instructions=persona_instructions,
            max_tokens=1000
        )
        
        if "На жаль" in llm_response and ("помилка" in llm_response or "недоступн" in llm_response):
            logging.warning(f"LLM повернув повідомлення про помилку: {llm_response}")
            # Якщо LLM повернув повідомлення про помилку, просто передаємо його користувачу
            await message.answer(llm_response)
        else:
            # Відповідаємо користувачу згенерованою відповіддю без меню
            logging.info("Відправляємо відповідь користувачу")
            await message.answer(
                llm_response,
                parse_mode="Markdown",
            )
        
    except Exception as e:
        logging.error(f"Помилка при обробці запиту: {e}")
        await message.answer(
            translation_manager.get_text("knowledge_base_error", language)
        )


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
