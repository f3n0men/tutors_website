from app import app, db
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    with app.app_context():
        try:
            # Удаляем все существующие таблицы
            logger.info("Удаление существующих таблиц...")
            db.drop_all()
            logger.info("Существующие таблицы удалены")

            # Создаем все таблицы заново
            logger.info("Создание новых таблиц...")
            db.create_all()
            logger.info("Таблицы успешно созданы!")

            # Проверяем подключение к базе данных
            logger.info("Проверка подключения к базе данных...")
            db.session.execute('SELECT 1')
            logger.info("Подключение к базе данных успешно!")

        except Exception as e:
            logger.error(f"Произошла ошибка: {str(e)}")
            raise

if __name__ == '__main__':
    create_tables() 