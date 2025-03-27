import os
import re
from typing import List, Optional

def read_knowledge_base(file_path: str = "knowledge_base.txt") -> str:
    """
    Читає вміст файлу бази знань.
    
    Args:
        file_path: Шлях до файлу бази знань
        
    Returns:
        Вміст файлу бази знань або порожній рядок, якщо файл не знайдено
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Помилка: Файл бази знань '{file_path}' не знайдено.")
        return ""
    except Exception as e:
        print(f"Помилка при читанні файлу бази знань: {e}")
        return ""

def find_relevant_context(query: str, knowledge_text: str, max_tokens: int = 1000) -> str:
    """
    Знаходить релевантні фрагменти тексту з бази знань на основі запиту.
    
    Args:
        query: Запит користувача
        knowledge_text: Текст бази знань
        max_tokens: Максимальна кількість токенів для повернення
        
    Returns:
        Рядок з релевантним контекстом або порожній рядок, якщо нічого не знайдено
    """
    if not knowledge_text or not query:
        return ""
    
    # Розділяємо базу знань на абзаци
    paragraphs = re.split(r'\n\s*\n', knowledge_text)
    
    # Підготовка запиту: видалення зайвих символів і перетворення на нижній регістр
    query = query.lower()
    query_words = set(re.findall(r'\w+', query))
    
    # Оцінка релевантності кожного абзацу
    scored_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        
        # Підрахунок кількості ключових слів з запиту в абзаці
        paragraph_lower = paragraph.lower()
        score = sum(1 for word in query_words if word in paragraph_lower)
        
        # Додатковий бонус для заголовків розділів, які містять ключові слова
        if paragraph.startswith('#') and score > 0:
            score += 2
        
        if score > 0:
            scored_paragraphs.append((score, paragraph))
    
    # Сортування абзаців за релевантністю (від найбільш до найменш релевантних)
    scored_paragraphs.sort(reverse=True, key=lambda x: x[0])
    
    # Формування контексту з найбільш релевантних абзаців
    context = ""
    for _, paragraph in scored_paragraphs:
        # Простий спосіб оцінки кількості токенів - приблизно 4 символи на токен
        estimated_tokens = len(context) // 4
        new_paragraph_tokens = len(paragraph) // 4
        
        if estimated_tokens + new_paragraph_tokens <= max_tokens:
            if context:
                context += "\n\n"
            context += paragraph
        else:
            break
    
    return context