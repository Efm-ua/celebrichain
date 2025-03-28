# bot.py (Виправлена версія)

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
# Імпортуємо тільки find_relevant_context, read_knowledge_base більше не потрібен тут
from knowledge_utils import find_relevant_context 
from llm_utils import generate_response

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Використовуємо logger замість root

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

# Словник для зберігання мовних налаштувань користувачів (просте рішення для MVP)
user_languages = {} 

# Функція для отримання мови користувача
def get_user_language(user_id: int) -> str:
    """Отримання мови користувача"""
    return user_languages.get(user_id, "en") # 'en' як мова за замовчуванням


# Функція для створення головної клавіатури
def get_main_keyboard(language: str) -> InlineKeyboardMarkup:
    """Створення головної інлайн-клавіатури"""
    builder = InlineKeyboardBuilder()
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
    builder.row(
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇲🇾 Bahasa Melayu", callback_data="lang_ms"),
    )
    return builder.as_markup()


# Функція для створення клавіатури повернення
def get_back_keyboard(language: str) -> InlineKeyboardMarkup:
    """Створення клавіатури з кнопкою повернення"""
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
    # Встановлюємо мову користувача або використовуємо 'en' за замовчуванням
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
    current_lang = get_user_language(user_id) # Поточна мова для тексту помилок/повідомлень

    # Обробка запитів зміни мови
    if callback.data.startswith("lang_"):
        selected_lang = callback.data.split('_')[1]
        
        if selected_lang == current_lang:
            # Відповідаємо на запит, щоб користувач бачив, що натискання оброблено
            await callback.answer(translation_manager.get_text('language_already_selected', current_lang))
            return
            
        user_languages[user_id] = selected_lang # Оновлюємо мову
        language = selected_lang # Використовуємо нову мову для відповіді
        
        welcome_text = translation_manager.get_text("welcome_message", language, user_name=callback.from_user.full_name)
        
        try:
            # Редагуємо повідомлення з новим текстом та клавіатурою
            await callback.message.edit_text(
                text=welcome_text,
                reply_markup=get_main_keyboard(language)
            )
        except Exception as e:
            logger.error(f"Помилка при редагуванні повідомлення для зміни мови: {e}")
            # Відповідаємо на callback, навіть якщо редагування не вдалося
            await callback.answer(translation_manager.get_text('error_occurred', language))
        return # Завершуємо обробку після зміни мови

    # Отримуємо мову користувача для інших колбеків
    language = get_user_language(user_id)

    # Обробка запиту FAQ
    if callback.data == "faq":
        faq_text = translation_manager.get_text("faq_text", language)
        try:
            await callback.message.edit_text(
                text=faq_text,
                reply_markup=get_back_keyboard(language),
                parse_mode="Markdown",
            )
        except Exception as e:
             logger.error(f"Помилка при редагуванні повідомлення для FAQ: {e}")
             await callback.answer(translation_manager.get_text('error_occurred', language))

    # Обробка запиту Info
    elif callback.data == "info":
        info_text = translation_manager.get_text("info_text", language)
        try:
            await callback.message.edit_text(
                text=info_text,
                reply_markup=get_back_keyboard(language),
                parse_mode="Markdown",
            )
        except Exception as e:
             logger.error(f"Помилка при редагуванні повідомлення для Info: {e}")
             await callback.answer(translation_manager.get_text('error_occurred', language))


    # Обробка запиту повернення до головного меню
    elif callback.data == "back":
        welcome_text = translation_manager.get_text(
            "welcome_message", language, user_name=callback.from_user.full_name
        )
        try:
            await callback.message.edit_text(
                text=welcome_text, reply_markup=get_main_keyboard(language)
            )
        except Exception as e:
             logger.error(f"Помилка при редагуванні повідомлення для повернення: {e}")
             await callback.answer(translation_manager.get_text('error_occurred', language))


    # За замовчуванням відповідаємо на callback, щоб прибрати годинник
    try:
        await callback.answer()
    except Exception as e:
        # Може виникнути помилка, якщо на колбек вже відповіли (напр., при помилці редагування)
        logger.debug(f"Не вдалося відповісти на callback (можливо, вже відповіли): {e}")


# Функція для читання інструкцій персони
def read_persona_instructions(file_path: str = "persona_instructions.txt") -> str:
    """Читає інструкції щодо стилю спілкування зірки з файлу"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Помилка: Файл інструкцій персони '{file_path}' не знайдено.")
        # Повертаємо базові інструкції англійською, якщо файл не знайдено
        return "You are a virtual assistant of a star. Respond friendly and informative." 
    except Exception as e:
        logger.error(f"Помилка при читанні файлу інструкцій персони: {e}")
        return "You are a virtual assistant of a star. Respond friendly and informative." # Базові інструкції у разі помилки


# Обробник для всіх текстових повідомлень (ВИПРАВЛЕНА ВЕРСІЯ)
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """Обробник для всіх текстових повідомлень"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    query = message.text
    if not query: # Ігноруємо порожні повідомлення
        return 
        
    logger.info(f"Отримано запит від користувача {user_id}: {query}")
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # --- ВИДАЛЕНО: Читання бази знань тут ---
        # knowledge_text = read_knowledge_base("knowledge_base.txt") 
        # if not knowledge_text: ... (ця перевірка більше не потрібна тут)
        
        logger.info("Пошук релевантного контексту...")
        # --- ОНОВЛЕНО ВИКЛИК find_relevant_context ---
        # Передаємо тільки query. max_tokens можна передати, якщо потрібно змінити значення за замовчуванням
        relevant_context = find_relevant_context(query, max_tokens=1000) 
        # --- КІНЕЦЬ ОНОВЛЕННЯ ---
        
        if not relevant_context:
            # Якщо релевантна інформація не знайдена функцією пошуку
            logger.info(f"Релевантний контекст не знайдено для запиту: {query}")
            # Використовуємо новий ключ перекладу
            await message.answer(
                translation_manager.get_text("context_not_found", language) 
            )
            return
        
        logger.info("Читаємо інструкції персони...")
        persona_instructions = read_persona_instructions() 
        # Перевірка на порожній рядок тут вже не потрібна, бо функція повертає дефолтний текст
        
        logger.info("Генеруємо відповідь за допомогою LLM...")
        llm_response = await generate_response(
            query=query,
            context=relevant_context,
            persona_instructions=persona_instructions,
            max_tokens=1000 # Ліміт токенів для відповіді LLM
        )
        
        # --- ПОКРАЩЕНА ОБРОБКА ВІДПОВІДІ LLM ---
        if llm_response is None:
            # Якщо generate_response повернула None (через помилку API тощо)
            logger.error(f"LLM не повернув відповідь для запиту: {query}")
            await message.answer(translation_manager.get_text("llm_error", language))
        # Перевірка на стандартні повідомлення про помилки від Anthropic (може потребувати уточнення)
        elif "sorry" in llm_response.lower() and ("cannot fulfill" in llm_response.lower() or "unable to process" in llm_response.lower()):
             logger.warning(f"LLM повернув повідомлення про неможливість обробки: {llm_response}")
             await message.answer(translation_manager.get_text("llm_error", language))
        else:
            # Успішна відповідь від LLM
            logger.info("Відправляємо відповідь користувачу")
            try:
                await message.answer(
                    llm_response,
                    # parse_mode="Markdown", # Обережно з Markdown, LLM може генерувати невалідний код
                    parse_mode=None # Безпечніше без parse_mode або використовувати HTML з екрануванням
                )
            except Exception as e:
                 logger.error(f"Помилка при відправці відповіді LLM користувачу: {e}")
                 # Спробувати відправити без parse_mode, якщо помилка була через нього
                 try:
                     await message.answer(llm_response, parse_mode=None)
                 except Exception as e_fallback:
                      logger.error(f"Помилка при повторній відправці відповіді LLM: {e_fallback}")
                      await message.answer(translation_manager.get_text("error_occurred", language))

        # --- КІНЕЦЬ ПОКРАЩЕНОЇ ОБРОБКИ ---

    except Exception as e:
        # Загальна обробка неочікуваних помилок
        logger.error(f"Неочікувана помилка при обробці запиту: {e}", exc_info=True) 
        await message.answer(
            translation_manager.get_text("error_occurred", language) # Використовуємо загальний ключ помилки
        )


# Функція для запуску бота
async def main() -> None:
    """Головна функція для запуску бота"""
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    # Ініціалізація та векторизація бази знань відбудеться при імпорті knowledge_utils
    # Тому важливо, щоб цей імпорт був до запуску main()
    logger.info("Запуск бота...")
    asyncio.run(main())