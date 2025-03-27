# Зірковий Помічник (Telegram-бот)

MVP Telegram-бота, який виступає в ролі персонального помічника для фанів малайзійської зірки. Бот відповідає на запитання фанів, використовуючи локальну базу знань та можливості мовної моделі Anthropic Claude.

## Функціональність

- Відповіді на запитання про зірку
- Імітація стилю спілкування зірки
- Використання локальної бази знань
- Інтеграція з Anthropic Claude 3.5 Sonnet

## Налаштування проекту

### Передумови

- Python 3.8 або новіше
- Telegram Bot Token (отриманий від BotFather)
- API ключ Anthropic

### Встановлення

1. Клонуйте репозиторій:

   ```
   git clone <url-репозиторію>
   cd celebrichain
   ```

2. Створіть віртуальне середовище та активуйте його:

   ```
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/MacOS
   source venv/bin/activate
   ```

3. Встановіть залежності:

   ```
   pip install -r requirements.txt
   ```

4. Створіть файл `.env` в корені проекту та додайте свої API ключі:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

### Запуск бота

```
python bot.py
```

## Структура проекту

- `bot.py` - основний файл бота
- `.env` - файл з API ключами (не включений до репозиторію)
- `requirements.txt` - залежності проекту

## Розробка

Проект знаходиться на стадії MVP (Minimum Viable Product) і буде розширюватися новими функціями.
