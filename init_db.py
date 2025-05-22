from app import app, db, Tutor, User
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    with app.app_context():
        try:
            # Проверяем подключение к базе данных
            logger.info("Проверка подключения к базе данных...")
            db.session.execute('SELECT 1')
            logger.info("Подключение к базе данных успешно!")

            # Проверяем, есть ли уже репетиторы
            if not Tutor.query.first():
                logger.info("Добавление начальных репетиторов...")
                # Добавляем начальных репетиторов
                tutors = [
                    Tutor(
                        name="Иван Иванов",
                        rating=4.9,
                        subjects="Математика, Физика",
                        image="tutor1.jpg",
                        likes=0,
                        dislikes=0
                    ),
                    Tutor(
                        name="Мария Петрова",
                        rating=4.7,
                        subjects="Английский язык",
                        image="tutor2.jpg",
                        likes=0,
                        dislikes=0
                    ),
                    Tutor(
                        name="Алексей Сидоров",
                        rating=4.8,
                        subjects="Информатика",
                        image="tutor3.jpg",
                        likes=0,
                        dislikes=0
                    )
                ]

                # Добавляем репетиторов в базу данных
                for tutor in tutors:
                    db.session.add(tutor)

                # Сохраняем изменения
                db.session.commit()
                logger.info("Начальные данные успешно добавлены!")
            else:
                logger.info("Репетиторы уже существуют в базе данных")

        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    init_db() 