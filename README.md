# Сайт репетиторов

Веб-приложение для поиска репетиторов с возможностью оценки и обратной связи.

## Функциональность

- Регистрация и авторизация пользователей
- Просмотр списка репетиторов
- Система оценок (лайки/дислайки)
- Личный кабинет с возможностью загрузки аватара
- Форма обратной связи с отправкой сообщений в Telegram

## Технологии

- Python 3.9
- Flask
- SQLAlchemy
- Flask-SocketIO
- SQLite (development) / PostgreSQL (production)

## Установка и запуск

1. Клонировать репозиторий:
```bash
git clone https://github.com/ваш-username/сайт-репетиторов.git
cd сайт-репетиторов
```

2. Создать виртуальное окружение и установить зависимости:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
pip install -r requirements.txt
```

3. Настроить переменные окружения:
- Создать файл `.env` и добавить:
```
FLASK_ENV=development
SECRET_KEY=ваш_секретный_ключ
BOT_TOKEN=ваш_telegram_bot_token
CHAT_ID=ваш_telegram_chat_id
```

4. Инициализировать базу данных:
```bash
flask db upgrade
```

5. Запустить приложение:
```bash
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Деплой

Приложение готово к развертыванию на:
- Railway.app
- Render.com
- Heroku

## Лицензия

MIT 