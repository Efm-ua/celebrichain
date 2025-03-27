import json
import os
from typing import Dict, Optional

class TranslationManager:
    """Клас для управління перекладами з JSON файлів"""
    
    def __init__(self, locales_dir: str = "locales"):
        """Ініціалізація менеджера перекладів
        
        Args:
            locales_dir: Шлях до директорії з файлами перекладів
        """
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "en"
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Завантаження всіх доступних перекладів з директорії locales"""
        if not os.path.exists(self.locales_dir):
            os.makedirs(self.locales_dir)
            
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                language_code = filename.split(".")[0]
                file_path = os.path.join(self.locales_dir, filename)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        self.translations[language_code] = json.load(file)
                except Exception as e:
                    print(f"Помилка завантаження перекладу {language_code}: {e}")
    
    def get_text(self, key: str, language: str, **kwargs) -> str:
        """Отримання перекладеного тексту за ключем
        
        Args:
            key: Ключ перекладу
            language: Код мови
            **kwargs: Параметри для форматування тексту
            
        Returns:
            Перекладений текст або ключ, якщо переклад не знайдено
        """
        # Якщо мова не підтримується, використовуємо мову за замовчуванням
        if language not in self.translations:
            language = self.default_language
            
        # Отримуємо переклад або повертаємо ключ, якщо переклад не знайдено
        text = self.translations.get(language, {}).get(key, key)
        
        # Форматуємо текст з переданими параметрами
        try:
            return text.format(**kwargs)
        except KeyError:
            # Якщо форматування не вдалося, повертаємо неформатований текст
            return text
    
    def get_available_languages(self) -> list:
        """Отримання списку доступних мов
        
        Returns:
            Список кодів доступних мов
        """
        return list(self.translations.keys())
    
    def set_default_language(self, language: str) -> None:
        """Встановлення мови за замовчуванням
        
        Args:
            language: Код мови
        """
        if language in self.translations:
            self.default_language = language

# Створення глобального екземпляру менеджера перекладів
translation_manager = TranslationManager()