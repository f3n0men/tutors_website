import os

class Config:
    # Базовая конфигурация
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cfd6245c36bd276cff4769d9fce4cf0dbc056f4e1a014c912cb9d23507bb3efe'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/avatars'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

class ProductionConfig(Config):
    # Production настройки
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    DEBUG = False
    
class DevelopmentConfig(Config):
    # Development настройки
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    DEBUG = True

# Выбор конфигурации на основе переменной окружения
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}