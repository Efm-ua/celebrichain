# knowledge_utils.py (Версія 6 - з Semantic Search)

import os
import re
import numpy as np
from typing import List, Optional, Tuple
import logging 
from langchain.text_splitter import RecursiveCharacterTextSplitter
# Додано імпорти для Sentence Transformers та Cosine Similarity
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG) # Розкоментуйте для ще більш детальних логів

# --- Константи та Глобальні Змінні ---
# Модель для векторизації (багатомовна, добре підходить для EN/MS)
MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2' 
KNOWLEDGE_BASE_PATH = "knowledge_base.txt"
CHUNK_SIZE = 400  # Розмір чанка в символах
CHUNK_OVERLAP = 80 # Перекриття чанків в символах
TOP_K = 7         # Кількість найбільш релевантних чанків для відбору

# Глобальні змінні для зберігання моделі, чанків та їх векторів
model: Optional[SentenceTransformer] = None
knowledge_chunks: List[str] = []
chunk_embeddings: Optional[np.ndarray] = None
# --- Кінець Констант та Глобальних Змінних ---


def read_knowledge_base(file_path: str = KNOWLEDGE_BASE_PATH) -> str:
    """
    Читає вміст файлу бази знань.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Помилка: Файл бази знань '{file_path}' не знайдено.")
        return ""
    except Exception as e:
        logger.error(f"Помилка при читанні файлу бази знань: {e}")
        return ""

def _initialize_splitter_and_model() -> Tuple[Optional[RecursiveCharacterTextSplitter], Optional[SentenceTransformer]]:
    """Ініціалізує спліттер та модель Sentence Transformer."""
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", ". ", ", ", " ", ""], 
        )
        # Завантажуємо модель один раз
        loaded_model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Модель SentenceTransformer '{MODEL_NAME}' успішно завантажено.")
        return splitter, loaded_model
    except Exception as e:
        logger.error(f"Помилка при ініціалізації спліттера або моделі SentenceTransformer: {e}", exc_info=True)
        return None, None

def _load_and_embed_knowledge():
    """
    Завантажує, розбиває на чанки та векторизує базу знань.
    Виконується один раз при завантаженні модуля.
    """
    global model, knowledge_chunks, chunk_embeddings 
    
    logger.info("Завантаження та векторизація бази знань...")
    knowledge_text = read_knowledge_base()
    if not knowledge_text:
        logger.error("Не вдалося завантажити базу знань. Пошук контексту буде недоступний.")
        return

    splitter, loaded_model = _initialize_splitter_and_model()
    
    if not splitter or not loaded_model:
        logger.error("Не вдалося ініціалізувати спліттер або модель. Пошук контексту буде недоступний.")
        return
        
    model = loaded_model # Зберігаємо модель глобально

    try:
        knowledge_chunks = splitter.split_text(knowledge_text)
        if not knowledge_chunks:
            logger.warning("Розбиття тексту не дало результатів (чанків).")
            knowledge_chunks = [] # Переконуємось, що це порожній список
            chunk_embeddings = np.array([]) # Порожній numpy масив
            return
            
        logger.info(f"Базу знань розбито на {len(knowledge_chunks)} чанків.")
        
        # Векторизація всіх чанків
        chunk_embeddings = model.encode(knowledge_chunks, show_progress_bar=True)
        logger.info(f"Чанки успішно векторизовано. Розмірність: {chunk_embeddings.shape}")

    except Exception as e:
        logger.error(f"Помилка під час розбиття або векторизації бази знань: {e}", exc_info=True)
        knowledge_chunks = []
        chunk_embeddings = None # Скидаємо ембеддінги у разі помилки

# --- Викликаємо функцію завантаження та векторизації при імпорті модуля ---
_load_and_embed_knowledge()
# --- 

def find_relevant_context(query: str, max_tokens: int = 1000) -> str:
    """
    Знаходить релевантні фрагменти тексту (чанки) за допомогою семантичного пошуку.
    
    Args:
        query: Запит користувача
        max_tokens: Максимальна кількість токенів для фінального контексту (приблизна)
        
    Returns:
        Рядок з релевантним контекстом або порожній рядок, якщо нічого не знайдено/помилка
    """
    global model, knowledge_chunks, chunk_embeddings
    logger.info(f"--- Starting find_relevant_context for query: '{query}' ---")

    # Перевірка, чи модель та вектори бази знань завантажено
    if model is None or chunk_embeddings is None or chunk_embeddings.size == 0 or not knowledge_chunks:
        logger.error("Модель або вектори бази знань не ініціалізовані. Неможливо виконати пошук.")
        return ""
        
    if not query:
        logger.warning("Query is empty, returning empty context.")
        return ""

    try:
        # 1. Векторизація запиту
        query_embedding = model.encode(query)
        
        # 2. Обчислення косинусної подібності
        # cosine_similarity очікує 2D масиви
        similarities = cosine_similarity(query_embedding.reshape(1, -1), chunk_embeddings)[0] 
        
        # 3. Відбір топ-K індексів
        # argsort повертає індекси, які б відсортували масив. Беремо останні K для найбільших значень.
        # Використовуємо partition замість argsort для ефективності, якщо K << N
        # top_k_indices = np.argsort(similarities)[-TOP_K:][::-1] # Варіант з argsort
        
        # Варіант з partition: знаходить K найбільших значень без повного сортування
        k_to_consider = min(TOP_K, len(knowledge_chunks)) # K не може бути більшим за кількість чанків
        if k_to_consider <= 0:
            logger.warning("k_to_consider is zero or negative.")
            return ""

        # Знаходимо індекси K найбільших елементів
        top_k_indices = np.argpartition(similarities, -k_to_consider)[-k_to_consider:]
        # Сортуємо ці K індексів за спаданням їх подібності
        top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])[::-1]]

        logger.debug(f"Top {k_to_consider} chunk indices: {top_k_indices}")
        logger.debug(f"Top {k_to_consider} similarities: {similarities[top_k_indices]}")

        # 4. Формування контексту з топ-K чанків
        context = ""
        current_word_count = 0 
        max_word_limit = int(max_tokens * 0.75) # Ліміт слів

        for i in top_k_indices:
            chunk = knowledge_chunks[i]
            score = similarities[i] # Оцінка подібності
            chunk_word_count = len(chunk.split())
            
            logger.debug(f"Considering chunk {i} score={score:.4f}. Context words: {current_word_count}, Chunk words: {chunk_word_count}, Limit: {max_word_limit}")
            
            # Перевірка ліміту слів
            if (current_word_count + chunk_word_count + 1) <= max_word_limit:
                if context: 
                    context += "\n\n" 
                context += chunk
                current_word_count += chunk_word_count + (1 if context else 0) 
                logger.debug(f"Added chunk {i}. Total words ~ {current_word_count}")
            else:
                logger.debug(f"Word limit ({max_word_limit}) reached based on chunk {i} score {score:.4f}. Breaking loop. Current words ~ {current_word_count}")
                break 
                
        if not context:
             logger.warning(f"Final context is empty after attempting to build it!")
        else:
             logger.info(f"Final context length (chars): {len(context)}, Estimated words: {current_word_count}")

        logger.info(f"--- Ending find_relevant_context ---")
        return context

    except Exception as e:
        logger.error(f"Помилка під час семантичного пошуку: {e}", exc_info=True)
        return "" # Повертаємо порожній рядок у разі помилки