# bot.py (Версія з виправленням NameError)

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
import asyncio 
from typing import Optional # Імпорт Optional, який був потрібен раніше

# Імпортуємо наші модулі
from translations import translation_manager
from database import init_db, add_log_entry, update_feedback 
from knowledge_utils import find_relevant_context 
from llm_utils import generate_response

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' 
    ) 
logger = logging.getLogger(__name__) 

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Отримання API ключів з змінних середовища
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
    logger.critical("!!! Валідний TELEGRAM_BOT_TOKEN не знайдено! Бот не може стартувати. !!!")
    raise ValueError(
        "Валідний TELEGRAM_BOT_TOKEN не знайдено в змінних середовища. Будь ласка, додайте справжній токен у файл .env"
    )

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    logging.warning(
        "Валідний ANTHROPIC_API_KEY не знайдено. Функціональність LLM буде недоступна."
    )

# Ініціалізація бота та диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=None) 
dp = Dispatcher()

# Словник для зберігання мовних налаштувань користувачів (просте рішення для MVP)
user_languages = {} 

# --- Функції для клавіатур та отримання мови ---
def get_user_language(user_id: int) -> str:
    return user_languages.get(user_id, "en") 

def get_main_keyboard(language: str) -> InlineKeyboardMarkup:
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

def get_back_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=translation_manager.get_text("button_back", language),
            callback_data="back",
        )
    )
    return builder.as_markup()

def get_feedback_keyboard(log_id: int) -> Optional[InlineKeyboardMarkup]: 
    """Створює клавіатуру з кнопками 👍/👎 для фідбеку."""
    if not isinstance(log_id, int) or log_id <= 0:
         logger.warning(f"Спроба створити клавіатуру фідбеку з невалідним log_id: {log_id}")
         return None 
         
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👍", callback_data=f"feedback:{log_id}:like"),
        InlineKeyboardButton(text="👎", callback_data=f"feedback:{log_id}:dislike")
    )
    return builder.as_markup()

# --- Обробники команд /start, /faq, /info ---
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id) 
    welcome_text = translation_manager.get_text(
        "welcome_message", language, user_name=message.from_user.full_name
    )
    await message.answer(text=welcome_text, reply_markup=get_main_keyboard(language))

@dp.message(Command("faq"))
async def command_faq_handler(message: Message) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)
    faq_text = translation_manager.get_text("faq_text", language)
    await message.answer(
        text=faq_text, reply_markup=get_back_keyboard(language), parse_mode="HTML" 
    )

@dp.message(Command("info"))
async def command_info_handler(message: Message) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)
    info_text = translation_manager.get_text("info_text", language)
    await message.answer(
        text=info_text, reply_markup=get_back_keyboard(language), parse_mode="HTML" 
    )

# --- Оновлений Обробник callback-запитів ---
@dp.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    """Обробник callback-запитів від інлайн-кнопок"""
    user_id = callback.from_user.id
    language = get_user_language(user_id) 

    processed = False 

    try:
        # Обробка фідбеку
        if callback.data and callback.data.startswith("feedback:"):
            processed = True 
            parts = callback.data.split(':')
            if len(parts) == 3:
                try:
                    log_id = int(parts[1])
                    action = parts[2] 

                    if action in ['like', 'dislike']:
                        success = await update_feedback(log_id, action)
                        
                        if success:
                            feedback_text = translation_manager.get_text('feedback_thanks', language)
                            await callback.answer(feedback_text, show_alert=False) 
                            try:
                                await callback.message.edit_reply_markup(reply_markup=None)
                            except Exception as edit_error:
                                logger.debug(f"Не вдалося прибрати клавіатуру фідбеку для log_id {log_id}: {edit_error}")
                        else:
                            await callback.answer(translation_manager.get_text('error_occurred', language), show_alert=True)
                    else:
                         logger.warning(f"Невідома дія у фідбек колбеку: {action} для log_id {log_id}")
                         await callback.answer(translation_manager.get_text('error_occurred', language), show_alert=True)
                            
                except (ValueError, IndexError) as parse_error:
                    logger.error(f"Помилка парсингу callback_data фідбеку: {callback.data}, Error: {parse_error}")
                    await callback.answer(translation_manager.get_text('error_occurred', language), show_alert=True)
            else:
                logger.error(f"Неправильний формат callback_data фідбеку: {callback.data}")
                await callback.answer(translation_manager.get_text('error_occurred', language), show_alert=True)
        
        # Обробка зміни мови
        elif callback.data and callback.data.startswith("lang_"):
            processed = True
            selected_lang = callback.data.split('_')[1]
            current_lang = get_user_language(user_id)
            if selected_lang != current_lang:
                if selected_lang in translation_manager.get_available_languages():
                    user_languages[user_id] = selected_lang
                    language = selected_lang 
                    welcome_text = translation_manager.get_text("welcome_message", language, user_name=callback.from_user.full_name)
                    await callback.message.edit_text(text=welcome_text, reply_markup=get_main_keyboard(language))
                else:
                    logger.warning(f"Спроба встановити непідтримувану мову: {selected_lang}")
                    await callback.answer("Unsupported language selected.", show_alert=True)
            else:
                 await callback.answer(translation_manager.get_text('language_already_selected', language))
        
        # Обробка FAQ
        elif callback.data == "faq":
            processed = True
            faq_text = translation_manager.get_text("faq_text", language)
            await callback.message.edit_text(text=faq_text, reply_markup=get_back_keyboard(language), parse_mode="HTML") 

        # Обробка Info
        elif callback.data == "info":
            processed = True
            info_text = translation_manager.get_text("info_text", language)
            await callback.message.edit_text(text=info_text, reply_markup=get_back_keyboard(language), parse_mode="HTML") 

        # Обробка Back
        elif callback.data == "back":
            processed = True
            welcome_text = translation_manager.get_text("welcome_message", language, user_name=callback.from_user.full_name)
            await callback.message.edit_text(text=welcome_text, reply_markup=get_main_keyboard(language))

        # Відповідаємо на колбек, тільки якщо він був нами оброблений і це не фідбек
        if processed and not callback.data.startswith("feedback:"):
            try:
                await callback.answer()
            except Exception:
                 logger.debug(f"Не вдалося відповісти на колбек {callback.data} (можливо, вже відповіли при помилці)")

    except Exception as e:
         logger.error(f"Помилка в callback_handler для data='{callback.data}': {e}", exc_info=True)
         try:
             await callback.answer(translation_manager.get_text('error_occurred', language), show_alert=True)
         except Exception:
             pass

# --- ДОДАНО ВИЗНАЧЕННЯ ФУНКЦІЇ ---
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
# --- КІНЕЦЬ ВИЗНАЧЕННЯ ФУНКЦІЇ ---


# --- Оновлений Обробник для всіх текстових повідомлень ---
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """Обробник для всіх текстових повідомлень"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    query = message.text
    if not query: 
        return 
        
    user_info_str = f"user_id={user_id}"
    if message.from_user.username:
         user_info_str += f", username=@{message.from_user.username}"
    if message.from_user.first_name:
         user_info_str += f", name='{message.from_user.first_name}'"
         
    logger.info(f"Отримано запит від користувача ({user_info_str}): '{query}'")
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    relevant_context: Optional[str] = None
    llm_response: Optional[str] = None
    log_id: Optional[int] = None
    final_bot_response: str = "" 

    try:
        logger.info("Пошук релевантного контексту...")
        relevant_context = find_relevant_context(query, max_tokens=1000) 
        
        if not relevant_context:
            logger.info(f"Релевантний контекст не знайдено для запиту: {query}")
            final_bot_response = translation_manager.get_text("context_not_found", language) 
            await message.answer(final_bot_response) 
            log_id = -2 
        else:
            logger.info("Читаємо інструкції персони...")
            # Тепер ця функція визначена вище
            persona_instructions = read_persona_instructions() 
            
            logger.info("Генеруємо відповідь за допомогою LLM...")
            llm_response = await generate_response(
                query=query,
                context=relevant_context,
                persona_instructions=persona_instructions,
                max_tokens=1000 
            )
            
            if llm_response is None:
                logger.error(f"LLM не повернув відповідь для запиту: {query}")
                final_bot_response = translation_manager.get_text("llm_error", language)
                await message.answer(final_bot_response)
                log_id = -3 
            elif isinstance(llm_response, str) and "sorry" in llm_response.lower() and ("cannot fulfill" in llm_response.lower() or "unable to process" in llm_response.lower() or "don't have enough information" in llm_response.lower()):
                 logger.warning(f"LLM повернув відповідь, схожу на помилку/відмову: {llm_response}")
                 final_bot_response = llm_response 
                 await message.answer(final_bot_response, parse_mode=None)
                 log_id = -4 
            else:
                final_bot_response = llm_response 
                logger.info("Запис логу перед відправкою відповіді...")
                log_id = await add_log_entry(
                     user_id=user_id,
                     user_first_name=message.from_user.first_name,
                     user_username=message.from_user.username,
                     user_query=query,
                     bot_response=final_bot_response, 
                     language=language,
                     retrieved_context=relevant_context 
                )
                
                feedback_markup = get_feedback_keyboard(log_id) if log_id and log_id > 0 else None

                logger.info(f"Відправляємо відповідь користувачу (log_id: {log_id})")
                await message.answer(
                    final_bot_response,
                    reply_markup=feedback_markup,
                    parse_mode=None 
                )
        
        # Записуємо в лог, якщо відповідь не була успішною відповіддю LLM, що вже залоговано, або контекст не знайдено
        if log_id is None or log_id <= 0: # Тепер включаємо -2, -3, -4
             logger.info(f"Запис логу для випадку без успішної відповіді LLM або без контексту (log_id: {log_id})...")
             # Викликаємо add_log_entry тільки якщо log_id не був встановлений (тобто не було успішної відповіді LLM, ЩО була залогована)
             # Або якщо log_id <= 0 (помилка контексту, помилка LLM, відмова LLM)
             await add_log_entry(
                 user_id=user_id,
                 user_first_name=message.from_user.first_name,
                 user_username=message.from_user.username,
                 user_query=query,
                 bot_response=final_bot_response, 
                 language=language,
                 retrieved_context=relevant_context 
             )
             
    except Exception as e:
        logger.error(f"Неочікувана помилка при обробці запиту: {e}", exc_info=True) 
        error_message_text = translation_manager.get_text("error_occurred", language)
        try:
            await message.answer(error_message_text)
        except Exception as send_err:
             logger.error(f"Не вдалося відправити повідомлення про помилку користувачу {user_id}: {send_err}")
             
        try:
             # Записуємо помилку в лог, навіть якщо відправка повідомлення про помилку не вдалась
             await add_log_entry(
                 user_id=user_id,
                 user_first_name=message.from_user.first_name,
                 user_username=message.from_user.username,
                 user_query=query,
                 bot_response=f"ERROR: {type(e).__name__} - {e}", 
                 language=language,
                 retrieved_context=relevant_context 
             )
        except Exception as db_err:
             logger.error(f"Не вдалося записати помилку в БД для користувача {user_id}: {db_err}")

# --- Функція для запуску бота ---
async def main() -> None:
    """Головна функція для запуску бота"""
    # Імпортуємо та викликаємо ініціалізацію БД тут
    from database import init_db
    await init_db() 
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Запуск поллінгу...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    # Векторизація бази знань відбудеться при імпорті knowledge_utils вище
    asyncio.run(main())