import os
import logging
import time
import asyncio
from typing import Optional, Dict, Any, Union

from anthropic import AsyncAnthropic, AuthenticationError, APIError, RateLimitError
from anthropic.types import MessageParam

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Максимальна кількість спроб при помилці rate limit
MAX_RETRIES = 5
# Базова затримка для експоненціального відступу (в секундах)
BASE_DELAY = 1


async def initialize_anthropic_client() -> Optional[AsyncAnthropic]:
    """
    Ініціалізує клієнт Anthropic з API-ключем зі змінних оточення.
    
    Returns:
        Клієнт AsyncAnthropic або None, якщо API-ключ не знайдено
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        logger.warning(
            "Валідний ANTHROPIC_API_KEY не знайдено в змінних середовища. Функціональність LLM недоступна."
        )
        return None
    
    return AsyncAnthropic(api_key=api_key)


async def generate_response(
    query: str, 
    context: str, 
    persona_instructions: str,
    max_tokens: int = 1000,
    model: str = "claude-3-5-sonnet-20240620"
) -> str:
    """
    Генерує відповідь від Claude на основі запиту користувача, контексту та інструкцій персони.
    
    Args:
        query: Запит користувача
        context: Контекст з бази знань
        persona_instructions: Інструкції щодо стилю спілкування зірки
        max_tokens: Максимальна кількість токенів для відповіді
        model: Назва моделі Claude для використання
        
    Returns:
        Згенерована відповідь або повідомлення про помилку
    """
    client = await initialize_anthropic_client()
    if not client:
        return "На жаль, сервіс відповідей тимчасово недоступний. Спробуйте пізніше."
    
    # Формування системного промпту
    system_prompt = f"""
    {persona_instructions}
    
    Важливі правила:
    1. Базуй свою відповідь ВИКЛЮЧНО на інформації, наданій у контексті нижче.
    2. Якщо в контексті немає відповіді на запитання, чесно визнай це.
    3. НІКОЛИ не вигадуй інформацію.
    4. Відповідай мовою запиту користувача.
    """
    
    # Формування основного промпту
    user_message = f"""
    <context>
    {context}
    </context>
    
    Запитання користувача: {query}
    """
    
    # Спроба отримати відповідь з експоненціальною затримкою при помилках
    retries = 0
    while retries <= MAX_RETRIES:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    MessageParam(role="user", content=user_message)
                ]
            )
            return response.content[0].text
            
        except RateLimitError as e:
            retries += 1
            if retries > MAX_RETRIES:
                logger.error(f"Перевищено ліміт спроб після помилки RateLimitError: {e}")
                return "На жаль, сервіс перевантажений. Будь ласка, спробуйте пізніше."
            
            # Експоненціальна затримка
            delay = BASE_DELAY * (2 ** (retries - 1))
            logger.warning(f"RateLimitError: затримка на {delay} секунд перед повторною спробою {retries}/{MAX_RETRIES}")
            await asyncio.sleep(delay)
            
        except AuthenticationError as e:
            logger.error(f"Помилка аутентифікації Anthropic API: {e}")
            return "На жаль, виникла проблема з аутентифікацією до сервісу відповідей. Зверніться до адміністратора."
            
        except APIError as e:
            logger.error(f"Помилка Anthropic API: {e}")
            return "На жаль, виникла помилка при обробці вашого запиту. Спробуйте пізніше."
            
        except Exception as e:
            logger.error(f"Неочікувана помилка при генерації відповіді: {e}")
            return "На жаль, виникла неочікувана помилка. Спробуйте пізніше."
    
    return "На жаль, сервіс відповідей тимчасово недоступний. Спробуйте пізніше."