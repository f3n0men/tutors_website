from app import app, db, Tutor, User
import os

def init_db():
    with app.app_context():
        # Проверяем, существует ли таблица
        inspector = db.inspect(db.engine)
        if not inspector.has_table("tutor"):
            # Создаем таблицы
            db.create_all()
            print("Таблицы созданы!")

        # Проверяем, есть ли уже репетиторы
        if not Tutor.query.first():
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

            try:
                # Добавляем репетиторов в базу данных
                for tutor in tutors:
                    db.session.add(tutor)

                # Сохраняем изменения
                db.session.commit()
                print("База данных инициализирована!")
            except Exception as e:
                print(f"Ошибка при инициализации базы данных: {e}")
                db.session.rollback()

if __name__ == '__main__':
    init_db() 