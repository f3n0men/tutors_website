from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
import logging
from config import config
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Загрузка конфигурации
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])
app.secret_key = os.environ.get('SECRET_KEY', 'cfd6245c36bd276cff4769d9fce4cf0dbc056f4e1a014c912cb9d23507bb3efe')

# Настройка папки для аватаров
app.config['UPLOAD_FOLDER'] = 'static/avatars'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Пути к файлам данных
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
REACTIONS_FILE = os.path.join(DATA_DIR, 'reactions.json')
TUTORS_FILE = os.path.join(DATA_DIR, 'tutors.json')

# Создаем директорию для данных, если её нет
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Функции для работы с данными
def load_data(file_path, default=None):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
    return default if default is not None else {}

def save_data(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")

# Загрузка данных
users = load_data(USERS_FILE, {})
reactions = load_data(REACTIONS_FILE, {})
tutors_data = load_data(TUTORS_FILE, [
    {
        "id": 1,
        "name": "Иван Иванов",
        "rating": 4.9,
        "subjects": "Математика, Физика",
        "image": "tutor1.jpg",
        "likes": 0,
        "dislikes": 0
    },
    {
        "id": 2,
        "name": "Мария Петрова",
        "rating": 4.7,
        "subjects": "Английский язык",
        "image": "tutor2.jpg",
        "likes": 0,
        "dislikes": 0
    },
    {
        "id": 3,
        "name": "Алексей Сидоров",
        "rating": 4.8,
        "subjects": "Информатика",
        "image": "tutor3.jpg",
        "likes": 0,
        "dislikes": 0
    }
])

# Сохраняем начальные данные, если файлы не существуют
if not os.path.exists(TUTORS_FILE):
    save_data(TUTORS_FILE, tutors_data)
if not os.path.exists(USERS_FILE):
    save_data(USERS_FILE, users)
if not os.path.exists(REACTIONS_FILE):
    save_data(REACTIONS_FILE, reactions)

# Настройка Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=None,
    logger=True,
    engineio_logger=True
)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    return render_template('index.html', user=users.get(session.get('user_email')))

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connection_success', {'status': 'connected'})
    for tutor in tutors_data:
        emit('reaction_update', {
            'tutor_id': tutor['id'],
            'likes': tutor['likes'],
            'dislikes': tutor['dislikes']
        })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('reaction')
def handle_socket_reaction(data):
    logger.info(f'Received reaction: {data}')
    try:
        # Проверка авторизации
        user_email = session.get('user_email')
        if not user_email:
            emit('reaction_error', {'message': 'Необходимо авторизоваться'})
            return

        tutor_id = str(data.get('tutor_id'))  # Преобразуем в строку для использования в качестве ключа
        reaction_type = data.get('type')
        
        if not all([tutor_id, reaction_type]) or reaction_type not in ['like', 'dislike']:
            emit('reaction_error', {'message': 'Неверные данные реакции'})
            return

        # Проверяем, не голосовал ли уже пользователь за этого репетитора
        user_reactions = reactions.setdefault(user_email, {})
        if tutor_id in user_reactions:
            emit('reaction_error', {'message': 'Вы уже оценили этого репетитора'})
            return

        # Находим репетитора по ID
        tutor = next((t for t in tutors_data if str(t['id']) == tutor_id), None)
        if not tutor:
            emit('reaction_error', {'message': 'Репетитор не найден'})
            return

        # Обновляем счетчики
        if reaction_type == 'like':
            tutor['likes'] += 1
        elif reaction_type == 'dislike':
            tutor['dislikes'] += 1

        # Сохраняем реакцию пользователя
        user_reactions[tutor_id] = reaction_type
        
        # Сохраняем обновленные данные
        save_data(REACTIONS_FILE, reactions)
        save_data(TUTORS_FILE, tutors_data)

        # Отправляем обновление всем клиентам
        response_data = {
            'tutor_id': int(tutor_id),  # Преобразуем обратно в число для фронтенда
            'likes': tutor['likes'],
            'dislikes': tutor['dislikes']
        }
        emit('reaction_update', response_data, broadcast=True)

    except Exception as e:
        logger.error(f'Error handling socket reaction: {str(e)}')
        logger.exception(e)
        emit('reaction_error', {'message': 'Произошла ошибка при обработке реакции'})

@app.route('/tutors')
def tutors_page():
    return render_template('tutors.html', tutors=tutors_data, user=users.get(session.get('user_email')))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        message = request.form['message']

        text = (f"Новая заявка:\nИмя: {name}\nТелефон: {phone}\n"
                f"Email: {email}\nСообщение: {message}")

        send_to_telegram(text)
        return redirect(url_for('contact'))

    return render_template('contact.html', user=users.get(session.get('user_email')))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if email in users:
            flash('Этот email уже зарегистрирован.', 'danger')
            return redirect(url_for('register'))

        users[email] = {
            'name': name,
            'password_hash': generate_password_hash(password),
            'role': role,
            'avatar': None
        }
        
        # Сохраняем обновленные данные пользователей
        save_data(USERS_FILE, users)

        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.get(email)

        if user and check_password_hash(user['password_hash'], password):
            session['user_email'] = email
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверный email или пароль.', 'danger')

    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_email' in session:
        user = users.get(session['user_email'])
        if request.method == 'POST':
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    user['avatar'] = filename
                    flash('Аватар успешно обновлен!', 'success')
                    return redirect(url_for('profile'))

        return render_template('profile.html', user=user)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('home'))

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

if __name__ == '__main__':
    # Настройка порта для Railway
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('FLASK_ENV') == 'production':
        # В production используем gunicorn
        socketio.run(app, host='0.0.0.0', port=port)
    else:
        # В development используем встроенный сервер Flask с socket.io
        socketio.run(app, host='0.0.0.0', port=port, debug=True)