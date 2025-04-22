# Telegram WebApp Auth Test

Цей проєкт дозволяє перевірити авторизацію користувача Telegram Mini App (WebApp) через HMAC (hash) та Ed25519 (signature).

## Встановлення

```bash
cd authtest
pip install -r requirements.txt
```

## Як отримати initData

1. Розмістіть файл `index.html` на будь-якому хостингу (або локально через ngrok/localhost).
2. Додайте посилання на цей сайт у BotFather як WebApp для вашого бота (Menu Button або через кнопку).
3. Запустіть Mini App через Telegram — у браузері зʼявиться поле з вашим `initData`.
4. Скопіюйте його для тестування бекенду.

## Використання CLI

```bash
python check_auth.py --init-data "<initData>" --bot-token "<bot_token>" --bot-id "<bot_id>"
```

- Для Ed25519 можна вказати свій публічний ключ через `--public-key`, за замовчуванням використовується production ключ Telegram.

## Файли

- `tg_webapp_auth.py` — бібліотека для перевірки підпису.
- `check_auth.py` — CLI-скрипт для перевірки.
- `requirements.txt` — залежності.
- `index.html` — Mini App для отримання initData.

## Приклад

```bash
python check_auth.py --init-data "auth_date=...&user=...&hash=...&signature=..." --bot-token "8079790761:AAEIxQPRZNF3hV7U5UKyDy4l5T4e31NqRR4" --bot-id "8079790761"
```
