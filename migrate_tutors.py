from app import app, db, Tutor

tutors_data = [
    {"name": "Иван Иванов", "rating": 4.9, "subjects": "Математика, Физика", "image": "tutor1.jpg"},
    {"name": "Мария Петрова", "rating": 4.7, "subjects": "Английский язык", "image": "tutor2.jpg"},
    {"name": "Алексей Сидоров", "rating": 4.8, "subjects": "Информатика", "image": "tutor3.jpg"},
]

def migrate_tutors():
    with app.app_context():
        for tutor_data in tutors_data:
            tutor = Tutor(
                name=tutor_data["name"],
                rating=tutor_data["rating"],
                subjects=tutor_data["subjects"],
                image=tutor_data["image"],
                likes=0,
                dislikes=0
            )
            db.session.add(tutor)
        db.session.commit()

if __name__ == "__main__":
    migrate_tutors() 