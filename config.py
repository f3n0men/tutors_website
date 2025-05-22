import os

class Config:
    # Базовая конфигурация
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cfd6245c36bd276cff4769d9fce4cf0dbc056f4e1a014c912cb9d23507bb3efe')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/avatars'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Настройка для работы с Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8186615018:AAENdDsVYsPPCQHfdeG17t7kENBrblWXupU')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '689163231')

class DevelopmentConfig(Config):
    # Development настройки
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    # Production настройки
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    DEBUG = False
    ENV = 'production'
    # Настройки для работы через прокси
    PREFERRED_URL_SCHEME = 'https'

# Выбор конфигурации на основе переменной окружения
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}