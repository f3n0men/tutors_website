from app import app, db

def create_tables():
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("Таблицы созданы успешно!")

if __name__ == '__main__':
    create_tables() 