# database.py

import logging
from datetime import datetime
from typing import Optional, Union

# Імпорти SQLAlchemy для асинхронної роботи
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, MetaData, Table, update, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite+aiosqlite:///history.db" # Назва файлу БД

# Створюємо асинхронний двигун SQLAlchemy
async_engine = create_async_engine(DATABASE_URL, echo=False) # echo=True для відладки SQL запитів

# Метадані для опису таблиць
metadata = MetaData()

# Опис таблиці conversation_log
conversation_log_table = Table(
    "conversation_log",
    metadata,
    Column("log_id", Integer, primary_key=True), # Автоінкремент за замовчуванням для SQLite
    Column("user_id", Integer, index=True),
    Column("user_first_name", String),
    Column("user_username", String, nullable=True),
    Column("timestamp_user", DateTime, default=datetime.utcnow), # Час запиту користувача
    Column("user_query", Text),
    Column("timestamp_bot", DateTime), # Час відповіді бота
    Column("bot_response", Text),
    Column("language", String(5)), # Код мови (en, ms)
    Column("retrieved_context", Text, nullable=True), # Збережений контекст (опціонально)
    Column("feedback", String(10), nullable=True, index=True) # 'like', 'dislike' або NULL
)

async def init_db():
    """Ініціалізує базу даних та створює таблицю, якщо її немає."""
    async with async_engine.begin() as conn:
        logger.info("Ініціалізація бази даних...")
        await conn.run_sync(metadata.create_all)
        logger.info("Таблиця 'conversation_log' перевірена/створена.")

# Фабрика асинхронних сесій
AsyncSessionFactory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def add_log_entry(
    user_id: int,
    user_first_name: str,
    user_username: Optional[str],
    user_query: str,
    bot_response: str,
    language: str,
    retrieved_context: Optional[str] = None,
) -> Optional[int]:
    """Додає новий запис про взаємодію до БД та повертає його ID."""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            try:
                timestamp_user = datetime.utcnow() # Беремо час перед записом запиту
                timestamp_bot = datetime.utcnow()  # Час відповіді - майже одразу після генерації

                new_log = conversation_log_table.insert().values(
                    user_id=user_id,
                    user_first_name=user_first_name,
                    user_username=user_username,
                    timestamp_user=timestamp_user, 
                    user_query=user_query,
                    timestamp_bot=timestamp_bot,
                    bot_response=bot_response,
                    language=language,
                    retrieved_context=retrieved_context,
                    feedback=None # Фідбек спочатку відсутній
                )
                result = await session.execute(new_log)
                await session.commit() # Commit після execute для insert з values
                
                # Отримання ID вставленого запису
                inserted_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
                
                if inserted_id:
                    logger.info(f"Запис логу {inserted_id} для користувача {user_id} додано до БД.")
                else:
                     logger.warning(f"Не вдалося отримати ID для нового запису логу користувача {user_id}.")
                return inserted_id
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Помилка SQLAlchemy при додаванні запису до БД: {e}", exc_info=True)
                return None
            except Exception as e:
                 await session.rollback()
                 logger.error(f"Неочікувана помилка при додаванні запису до БД: {e}", exc_info=True)
                 return None


async def update_feedback(log_id: int, feedback_value: str):
    """Оновлює поле feedback для зазначеного запису логу."""
    if not isinstance(log_id, int) or log_id <= 0:
        logger.warning(f"Спроба оновити фідбек з невалідним log_id: {log_id}")
        return False
        
    if feedback_value not in ['like', 'dislike']:
        logger.warning(f"Спроба оновити фідбек з невалідним значенням: {feedback_value}")
        return False

    async with AsyncSessionFactory() as session:
        async with session.begin():
            try:
                stmt = (
                    update(conversation_log_table)
                    .where(conversation_log_table.c.log_id == log_id)
                    .values(feedback=feedback_value)
                )
                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(f"Фідбек '{feedback_value}' для запису логу {log_id} оновлено.")
                    return True
                else:
                    logger.warning(f"Запис логу з ID {log_id} не знайдено для оновлення фідбеку.")
                    return False
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Помилка SQLAlchemy при оновленні фідбеку для log_id {log_id}: {e}", exc_info=True)
                return False
            except Exception as e:
                await session.rollback()
                logger.error(f"Неочікувана помилка при оновленні фідбеку для log_id {log_id}: {e}", exc_info=True)
                return False