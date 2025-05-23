from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
import logging
from config import config
import json
from functools import wraps

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
    user_email = session.get('user_email')
    user = users.get(user_email) if user_email else None
    # Если в сессии есть email, но пользователя нет - очищаем сессию
    if user_email and not user:
        session.clear()
        return redirect(url_for('home'))
    return render_template('index.html', user=user)

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
    user_email = session.get('user_email')
    user = users.get(user_email) if user_email else None
    # Если в сессии есть email, но пользователя нет - очищаем сессию
    if user_email and not user:
        session.clear()
        return redirect(url_for('tutors_page'))
    return render_template('tutors.html', tutors=tutors_data, user=user)

def send_to_telegram(message):
    """Отправка сообщения в Telegram"""
    bot_token = app.config['TELEGRAM_BOT_TOKEN']
    chat_id = app.config['TELEGRAM_CHAT_ID']
    
    if not bot_token or not chat_id:
        logger.error("Telegram bot token or chat ID not configured")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return False

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        message = request.form.get('message')

        if not all([name, phone, email, message]):
            flash('Пожалуйста, заполните все поля формы.', 'danger')
            return redirect(url_for('contact'))

        text = f"""
<b>Новая заявка с сайта!</b>

<b>Имя:</b> {name}
<b>Телефон:</b> {phone}
<b>Email:</b> {email}
<b>Сообщение:</b>
{message}
"""
        if send_to_telegram(text):
            flash('Ваше сообщение успешно отправлено!', 'success')
        else:
            flash('Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.', 'danger')
            
        return redirect(url_for('contact'))

    return render_template('contact.html', user=users.get(session.get('user_email')))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = 'admin' if not users else 'user'  # Первый зарегистрированный пользователь становится админом

        if email in users:
            flash('Этот email уже зарегистрирован.', 'danger')
            return redirect(url_for('register'))

        users[email] = {
            'name': name,
            'password_hash': generate_password_hash(password),
            'role': role,
            'avatar': None
        }
        
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
    user_email = session.get('user_email')
    if not user_email:
        flash('Необходимо войти в систему.', 'danger')
        return redirect(url_for('login'))

    user = users.get(user_email)
    if not user:
        session.clear()
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                if allowed_file(file.filename):
                    try:
                        # Создаем папку для аватаров, если её нет
                        avatars_folder = os.path.join('static', 'avatars')
                        if not os.path.exists(avatars_folder):
                            os.makedirs(avatars_folder)
                        
                        # Генерируем уникальное имя файла
                        filename = secure_filename(f"{user_email}_{file.filename}")
                        filepath = os.path.join(avatars_folder, filename)
                        
                        # Сохраняем файл
                        file.save(filepath)
                        
                        # Обновляем информацию о пользователе
                        user['avatar'] = filename
                        save_data(USERS_FILE, users)
                        
                        flash('Аватар успешно обновлен!', 'success')
                    except Exception as e:
                        logger.error(f"Error saving avatar: {e}")
                        flash('Ошибка при сохранении аватара.', 'danger')
                else:
                    flash('Недопустимый формат файла. Разрешены только изображения (png, jpg, jpeg, gif).', 'danger')

    return render_template('profile.html', user=user, email=user_email)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('home'))

def is_admin():
    """Проверяет, является ли текущий пользователь администратором"""
    user_email = session.get('user_email')
    if not user_email:
        return False
    user = users.get(user_email)
    return user and user.get('role') == 'admin'

def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_panel():
    """Панель администратора"""
    return render_template('admin.html', users=users)

@app.route('/admin/change-role', methods=['POST'])
@admin_required
def change_role():
    """Изменение роли пользователя"""
    email = request.form.get('email')
    new_role = request.form.get('role')
    
    if not email or not new_role or new_role not in ['user', 'admin']:
        flash('Неверные параметры запроса.', 'danger')
        return redirect(url_for('admin_panel'))
    
    if email not in users:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Запрещаем администратору понизить свою роль
    if email == session.get('user_email') and new_role != 'admin':
        flash('Вы не можете понизить свою роль.', 'danger')
        return redirect(url_for('admin_panel'))
    
    users[email]['role'] = new_role
    save_data(USERS_FILE, users)
    flash(f'Роль пользователя {email} изменена на {new_role}.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-user', methods=['POST'])
@admin_required
def delete_user():
    """Удаление пользователя"""
    email = request.form.get('email')
    
    if not email:
        flash('Email не указан.', 'danger')
        return redirect(url_for('admin_panel'))
    
    if email not in users:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Запрещаем администратору удалить самого себя
    if email == session.get('user_email'):
        flash('Вы не можете удалить свой аккаунт.', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Удаляем аватар пользователя, если он есть
    user = users[email]
    if user.get('avatar'):
        avatar_path = os.path.join('static', 'avatars', user['avatar'])
        try:
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        except Exception as e:
            logger.error(f"Error removing avatar: {e}")
    
    # Удаляем реакции пользователя
    if email in reactions:
        del reactions[email]
        save_data(REACTIONS_FILE, reactions)
    
    # Удаляем пользователя
    del users[email]
    save_data(USERS_FILE, users)
    
    flash(f'Пользователь {email} успешно удален.', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    # Настройка порта для Railway
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('FLASK_ENV') == 'production':
        # В production используем gunicorn
        socketio.run(app, host='0.0.0.0', port=port)
    else:
        # В development используем встроенный сервер Flask с socket.io
        socketio.run(app, host='0.0.0.0', port=port, debug=True)